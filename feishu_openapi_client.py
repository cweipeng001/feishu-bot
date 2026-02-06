#!/usr/bin/env python3
"""
飞书 OpenAPI MCP 客户端
通过 JSON-RPC 直接调用本地 OpenAPI MCP 服务
"""

import os
import json
import logging
import subprocess
import threading
import time
import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_SEARCH_COUNT = 3
MAX_CONTENT_LENGTH = 4000
MCP_SERVER_PORT = 3000  # OpenAPI MCP 默认端口

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

class FeishuOpenAPIClient:
    """飞书 OpenAPI 客户端"""
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self._lock = threading.Lock()
        
    def start_mcp_service(self) -> bool:
        """启动 OpenAPI MCP 服务"""
        with self._lock:
            if self.process and self.process.poll() is None:
                logger.info("✅ OpenAPI MCP 服务已在运行")
                return True
            
            try:
                logger.info("🚀 启动 OpenAPI MCP 服务...")
                
                # 构建命令
                cmd = [
                    "npx", "-y", "@larksuiteoapi/lark-mcp", "mcp",
                    "-a", self.app_id,
                    "-s", self.app_secret,
                    "--oauth",
                    "--port", str(MCP_SERVER_PORT)
                ]
                
                # 启动进程
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    text=True
                )
                
                # 等待服务启动
                time.sleep(3)
                
                if self.process.poll() is None:
                    logger.info("✅ OpenAPI MCP 服务启动成功")
                    return True
                else:
                    logger.error("❌ OpenAPI MCP 服务启动失败")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ 启动 OpenAPI MCP 服务失败: {e}")
                return False
    
    def stop_mcp_service(self):
        """停止 OpenAPI MCP 服务"""
        with self._lock:
            if self.process:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=5)
                    logger.info("⏹️ OpenAPI MCP 服务已停止")
                except:
                    self.process.kill()
                finally:
                    self.process = None
    
    def _get_next_id(self) -> int:
        """获取下一个请求 ID"""
        self.request_id += 1
        return self.request_id
    
    def _call_mcp_method(self, method: str, params: Dict = None) -> Optional[Dict]:
        """
        调用 MCP 方法
        
        Args:
            method: MCP 方法名
            params: 参数
            
        Returns:
            响应结果
        """
        if not self.start_mcp_service():
            return None
        
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": self._get_next_id(),
                "method": method
            }
            
            if params:
                payload["params"] = params
            
            logger.info(f"📡 调用 MCP 方法: {method}")
            
            response = requests.post(
                f"http://localhost:{MCP_SERVER_PORT}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if "error" in result:
                    logger.error(f"❌ MCP 错误: {result['error']}")
                    return None
                return result.get("result")
            else:
                logger.error(f"❌ MCP 请求失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ MCP 调用失败: {e}")
            return None
    
    def initialize(self) -> bool:
        """初始化 MCP 连接"""
        result = self._call_mcp_method("initialize")
        if result:
            logger.info(f"✅ MCP 初始化成功: {result}")
            return True
        return False
    
    def list_tools(self) -> Optional[List[Dict]]:
        """列出可用工具"""
        result = self._call_mcp_method("tools/list")
        if result and "tools" in result:
            tools = result["tools"]
            logger.info(f"🔧 可用工具数量: {len(tools)}")
            for tool in tools:
                logger.info(f"  - {tool.get('name', 'Unknown')}: {tool.get('description', '')[:50]}...")
            return tools
        return None
    
    def call_tool(self, tool_name: str, arguments: Dict) -> Optional[Any]:
        """
        调用具体工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        result = self._call_mcp_method("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        
        if result:
            logger.info(f"✅ 工具 {tool_name} 调用成功")
            return result
        return None

class FeishuOpenAPIDocsManager:
    """飞书 OpenAPI 文档管理器"""
    
    def __init__(self, app_id: str, app_secret: str, max_content_length: int = MAX_CONTENT_LENGTH):
        self.max_content_length = max_content_length
        self.client = FeishuOpenAPIClient(app_id, app_secret)
    
    def search_documents(self, query: str, count: int = DEFAULT_SEARCH_COUNT) -> List[SearchResult]:
        """
        搜索文档（使用 wiki.v1.node.search）
        """
        try:
            logger.info(f"🔍 搜索文档: '{query}'")
            
            # 初始化连接
            if not self.client.initialize():
                logger.error("❌ MCP 初始化失败")
                return []
            
            # 列出工具确认可用性
            tools = self.client.list_tools()
            if not tools:
                logger.error("❌ 无法获取工具列表")
                return []
            
            # 检查是否有搜索工具
            search_tools = [tool for tool in tools if 'search' in tool.get('name', '').lower()]
            logger.info(f"🔍 找到搜索相关工具: {[t.get('name') for t in search_tools]}")
            
            # 调用 wiki.v1.node.search
            result = self.client.call_tool("wiki.v1.node.search", {
                "query": query,
                "page_size": count
            })
            
            if result:
                # 解析搜索结果
                search_results = []
                nodes = result.get("nodes", [])
                
                for node in nodes[:count]:
                    search_results.append(SearchResult(
                        doc_token=node.get("node_token", ""),
                        doc_type="wiki",
                        title=node.get("title", "未知标题"),
                        url=node.get("url", ""),
                        owner_name=node.get("owner", {}).get("name", ""),
                        create_time=str(node.get("create_time", "")),
                        update_time=str(node.get("update_time", ""))
                    ))
                
                logger.info(f"✅ 找到 {len(search_results)} 个文档")
                return search_results
            
            return []
            
        except Exception as e:
            logger.error(f"❌ 文档搜索失败: {e}")
            return []
    
    def get_document_content(self, doc_token: str) -> Optional[DocumentContent]:
        """
        获取文档内容（使用 docx.v1.document.rawContent）
        """
        try:
            logger.info(f"📄 获取文档内容: {doc_token}")
            
            # 初始化连接
            if not self.client.initialize():
                return None
            
            # 调用 docx.v1.document.rawContent
            result = self.client.call_tool("docx.v1.document.rawContent", {
                "document_id": doc_token
            })
            
            if result:
                content = result.get("content", "")
                title = result.get("title", "未知标题")
                
                # 清洗和截断内容
                cleaned_content, truncated, original_length = self._clean_and_truncate(content)
                
                return DocumentContent(
                    doc_token=doc_token,
                    title=title,
                    content=cleaned_content,
                    doc_type="docx",
                    url=f"https://k7ftx11633c.feishu.cn/docx/{doc_token}",
                    truncated=truncated,
                    original_length=original_length
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 获取文档内容失败: {e}")
            return None
    
    def _clean_and_truncate(self, content: str) -> tuple:
        """清洗和截断文档内容"""
        if not content:
            return "", False, 0
        
        original_length = len(content)
        
        # 截断到最大长度
        truncated = False
        if len(content) > self.max_content_length:
            content = content[:self.max_content_length]
            content += "\n\n...(内容已截断)"
            truncated = True
        
        return content.strip(), truncated, original_length
    
    def search_and_retrieve(self, query: str, count: int = DEFAULT_SEARCH_COUNT) -> List[DocumentContent]:
        """搜索并获取文档内容"""
        search_results = self.search_documents(query, count)
        documents = []
        
        for result in search_results:
            content = self.get_document_content(result.doc_token)
            if content:
                content.title = result.title
                content.url = result.url
                documents.append(content)
        
        return documents
    
    def format_for_llm(self, documents: List[DocumentContent]) -> str:
        """格式化为 LLM 可用的上下文"""
        if not documents:
            return "未找到相关文档。"
        
        formatted_parts = ["📚 **检索到的飞书文档内容：**\n"]
        
        for i, doc in enumerate(documents, 1):
            truncate_hint = " (内容已截断)" if doc.truncated else ""
            
            part = f"""
---
### 📄 文档 {i}: {doc.title}
- 链接: {doc.url}
{truncate_hint}

**内容:**
{doc.content}
"""
            formatted_parts.append(part)
        
        formatted_parts.append("\n---\n以上是检索到的文档内容，请基于这些信息回答用户问题。")
        return "\n".join(formatted_parts)

# 全局实例管理
_managers: Dict[str, FeishuOpenAPIDocsManager] = {}

def get_openapi_docs_manager(app_id: str = None, app_secret: str = None) -> FeishuOpenAPIDocsManager:
    """获取 OpenAPI 文档管理器实例"""
    global _managers
    
    # 从环境变量获取默认值
    if not app_id:
        app_id = os.getenv("FEISHU_APP_ID")
    if not app_secret:
        app_secret = os.getenv("FEISHU_APP_SECRET")
    
    if not app_id or not app_secret:
        raise ValueError("请提供飞书 App ID 和 App Secret")
    
    key = f"{app_id}_{app_secret}"
    if key not in _managers:
        _managers[key] = FeishuOpenAPIDocsManager(app_id, app_secret)
    
    return _managers[key]

def search_feishu_knowledge_openapi(query: str, count: int = 3) -> str:
    """使用 OpenAPI MCP 搜索飞书知识库"""
    try:
        manager = get_openapi_docs_manager()
        documents = manager.search_and_retrieve(query, count)
        return manager.format_for_llm(documents)
    except Exception as e:
        logger.error(f"OpenAPI 搜索失败: {e}")
        return f"❌ OpenAPI 搜索失败: {str(e)}"

# 程序退出时清理资源
import atexit
atexit.register(lambda: [manager.client.stop_mcp_service() for manager in _managers.values()])