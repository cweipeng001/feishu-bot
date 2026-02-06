#!/usr/bin/env python3
"""
飞书官方 MCP 服务客户端
对接飞书官方提供的远程 MCP 服务
"""

import os
import json
import logging
import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """文档搜索结果"""
    doc_token: str
    doc_type: str
    title: str
    url: str
    owner_name: str = ""
    create_time: str = ""
    update_time: str = ""

@dataclass
class DocumentContent:
    """文档内容"""
    doc_token: str
    title: str
    content: str
    doc_type: str
    url: str
    truncated: bool = False
    original_length: int = 0

class FeishuOfficialMCPClient:
    """飞书官方 MCP 客户端"""
    
    def __init__(self, mcp_server_url: str = None):
        """
        初始化 MCP 客户端
        
        Args:
            mcp_server_url: 飞书官方 MCP 服务 URL
                          从 https://open.feishu.cn/page/mcp 获取
        """
        self.mcp_server_url = mcp_server_url or os.getenv("FEISHU_OFFICIAL_MCP_URL")
        self._request_id = 0
        
        if not self.mcp_server_url:
            raise ValueError("请提供飞书官方 MCP 服务 URL，可通过环境变量 FEISHU_OFFICIAL_MCP_URL 设置")
        
        logger.info(f"🚀 初始化飞书官方 MCP 客户端")
        logger.info(f"📡 服务地址: {self.mcp_server_url}")
    
    def _get_next_id(self) -> int:
        """获取下一个请求 ID"""
        self._request_id += 1
        return self._request_id
    
    def _call_mcp(self, method: str, params: Dict = None) -> Optional[Dict[str, Any]]:
        """
        调用 MCP 服务
        
        Args:
            method: MCP 方法名
            params: 请求参数
            
        Returns:
            响应结果
        """
        # 获取用户访问令牌
        from feishu_auth import get_user_access_token
        user_token = get_user_access_token()
        
        if not user_token:
            logger.error("❌ 未获取到用户访问令牌，请先完成 OAuth 授权")
            return None
        
        payload = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": method
        }
        
        if params:
            payload["params"] = params
        
        logger.info(f"📡 调用官方 MCP: {method}")
        
        # 尝试不同的认证头
        auth_headers = [
            {"Content-Type": "application/json", "Authorization": f"Bearer {user_token}"},
            {"Content-Type": "application/json", "X-Lark-MCP-UAT": user_token},
            {"Content-Type": "application/json"}  # 无认证
        ]
        
        for i, headers in enumerate(auth_headers):
            try:
                logger.info(f"📡 尝试认证方式 {i+1}/{len(auth_headers)}")
                response = requests.post(
                    self.mcp_server_url,
                    json=payload,
                    timeout=30,
                    headers=headers
                )
                
                logger.info(f"📡 MCP 响应状态: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 检查错误
                    if "error" in result:
                        error = result["error"]
                        logger.error(f"❌ MCP 错误: code={error.get('code')}, msg={error.get('message')}")
                        continue
                    
                    return result.get("result", {})
                else:
                    logger.error(f"❌ MCP 请求失败: HTTP {response.status_code}")
                    logger.error(f"❌ 响应内容: {response.text}")
                    
            except Exception as e:
                logger.error(f"❌ MCP 请求异常: {e}")
                continue
        
        return None
    
    def initialize(self) -> bool:
        """初始化 MCP 连接"""
        result = self._call_mcp("initialize")
        if result:
            logger.info(f"✅ MCP 初始化成功: {result.get('serverInfo', {})}")
            return True
        return False
    
    def list_tools(self) -> List[Dict]:
        """列出可用工具"""
        result = self._call_mcp("tools/list")
        if result:
            tools = result.get("tools", [])
            logger.info(f"✅ 获取到 {len(tools)} 个可用工具")
            for tool in tools:
                logger.info(f"  - {tool.get('name')}: {tool.get('description', '')}")
            return tools
        return []
    
    def call_tool(self, tool_name: str, arguments: Dict) -> Optional[Dict]:
        """
        调用指定工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        result = self._call_mcp("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        
        if result:
            logger.info(f"✅ 工具 '{tool_name}' 调用成功")
            return result
        
        logger.error(f"❌ 工具 '{tool_name}' 调用失败")
        return None

class FeishuOfficialDocsManager:
    """飞书官方文档管理器"""
    
    def __init__(self, mcp_server_url: str = None, max_content_length: int = 4000):
        self.max_content_length = max_content_length
        self.client = FeishuOfficialMCPClient(mcp_server_url)
        self._initialized = False
    
    def _ensure_initialized(self) -> bool:
        """确保 MCP 客户端已初始化"""
        if not self._initialized:
            if self.client.initialize():
                # 列出可用工具
                self.client.list_tools()
                self._initialized = True
            else:
                logger.error("❌ MCP 客户端初始化失败")
                return False
        return True
    
    def search_documents(self, query: str, count: int = 3) -> List[SearchResult]:
        """
        搜索飞书文档
        
        Args:
            query: 搜索关键词
            count: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        if not self._ensure_initialized():
            return []
        
        logger.info(f"🔍 搜索飞书文档: '{query}'")
        
        try:
            # 调用 search-doc 工具
            result = self.client.call_tool("search-doc", {
                "query": query,
                "count": count
            })
            
            if not result:
                logger.info("📚 搜索无结果")
                return []
            
            # 解析搜索结果
            search_results = []
            
            # 尝试多种可能的数据结构
            docs = (result.get("docs") or 
                   result.get("data", {}).get("docs") or 
                   result.get("content", []))
            
            if isinstance(docs, list):
                for doc in docs[:count]:
                    search_results.append(SearchResult(
                        doc_token=doc.get("doc_token") or doc.get("docToken") or doc.get("token", ""),
                        doc_type=doc.get("doc_type") or doc.get("docType") or "docx",
                        title=doc.get("title", "未知标题"),
                        url=doc.get("url") or doc.get("doc_url", ""),
                        owner_name=doc.get("owner_name") or doc.get("owner", ""),
                        create_time=str(doc.get("create_time", "")),
                        update_time=str(doc.get("update_time", ""))
                    ))
            
            logger.info(f"✅ 搜索到 {len(search_results)} 个文档")
            return search_results
            
        except Exception as e:
            logger.error(f"❌ 文档搜索失败: {e}")
            return []
    
    def get_document_content(self, doc_token: str, doc_type: str = "docx") -> Optional[DocumentContent]:
        """
        获取文档内容
        
        Args:
            doc_token: 文档 Token
            doc_type: 文档类型
            
        Returns:
            文档内容对象
        """
        if not self._ensure_initialized():
            return None
        
        logger.info(f"📄 获取文档内容: {doc_token}")
        
        try:
            # 调用 fetch-doc 工具
            result = self.client.call_tool("fetch-doc", {
                "doc_token": doc_token,
                "doc_type": doc_type
            })
            
            if result:
                content = result.get("content", "")
                title = result.get("title", "未知文档")
                url = result.get("url", "")
                
                # 处理内容长度限制
                original_length = len(content)
                truncated = False
                
                if len(content) > self.max_content_length:
                    content = content[:self.max_content_length] + "\n\n... [内容已截断]"
                    truncated = True
                
                logger.info(f"✅ 成功获取文档内容 ({len(content)} 字符)")
                
                return DocumentContent(
                    doc_token=doc_token,
                    title=title,
                    content=content,
                    doc_type=doc_type,
                    url=url,
                    truncated=truncated,
                    original_length=original_length
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 获取文档内容失败: {e}")
            return None

# 全局实例管理
_managers: Dict[str, FeishuOfficialDocsManager] = {}

def get_official_docs_manager(mcp_server_url: str = None) -> FeishuOfficialDocsManager:
    """
    获取飞书官方文档管理器实例
    
    Args:
        mcp_server_url: MCP 服务 URL
        
    Returns:
        文档管理器实例
    """
    # 使用 URL 作为 key
    key = mcp_server_url or os.getenv("FEISHU_OFFICIAL_MCP_URL", "default")
    
    if key not in _managers:
        _managers[key] = FeishuOfficialDocsManager(mcp_server_url)
    
    return _managers[key]

def search_feishu_documents_official(query: str, count: int = 3, 
                                   mcp_server_url: str = None) -> List[SearchResult]:
    """
    搜索飞书文档（官方 MCP 方式）
    
    Args:
        query: 搜索关键词
        count: 返回结果数量
        mcp_server_url: MCP 服务 URL
        
    Returns:
        搜索结果列表
    """
    manager = get_official_docs_manager(mcp_server_url)
    return manager.search_documents(query, count)

def get_feishu_document_content_official(doc_token: str, doc_type: str = "docx",
                                       mcp_server_url: str = None) -> Optional[DocumentContent]:
    """
    获取飞书文档内容（官方 MCP 方式）
    
    Args:
        doc_token: 文档 Token
        doc_type: 文档类型
        mcp_server_url: MCP 服务 URL
        
    Returns:
        文档内容对象
    """
    manager = get_official_docs_manager(mcp_server_url)
    return manager.get_document_content(doc_token, doc_type)

# 测试函数
def test_official_mcp():
    """测试官方 MCP 功能"""
    try:
        print("🚀 测试飞书官方 MCP 服务...")
        
        # 从环境变量获取 URL
        mcp_url = os.getenv("FEISHU_OFFICIAL_MCP_URL")
        if not mcp_url:
            print("❌ 请设置环境变量 FEISHU_OFFICIAL_MCP_URL")
            return
        
        print(f"📡 使用 MCP 服务: {mcp_url}")
        
        # 创建客户端
        client = FeishuOfficialMCPClient(mcp_url)
        
        # 初始化
        if not client.initialize():
            print("❌ 初始化失败")
            return
        
        # 列出工具
        tools = client.list_tools()
        if not tools:
            print("❌ 无法获取工具列表")
            return
        
        # 测试搜索
        print("\n🔍 测试文档搜索...")
        search_result = client.call_tool("search-doc", {
            "query": "测试",
            "count": 2
        })
        
        if search_result:
            print("✅ 搜索成功!")
            print(f"结果: {json.dumps(search_result, ensure_ascii=False, indent=2)[:200]}...")
        else:
            print("❌ 搜索失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_official_mcp()