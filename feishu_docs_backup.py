#!/usr/bin/env python3
"""
飞书云文档检索模块
使用飞书 MCP (Model Context Protocol) 远程服务实现文档搜索和内容获取
"""

import os
import re
import json
import logging
import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

from feishu_auth import get_user_access_token, is_user_authorized

load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# 飞书 MCP 服务配置
# ============================================================
FEISHU_MCP_URL = "https://mcp.feishu.cn/mcp"
MCP_ALLOWED_TOOLS = "search-doc,fetch-doc"

# 默认配置
DEFAULT_SEARCH_COUNT = 3
MAX_CONTENT_LENGTH = 4000  # 限制返回给 LLM 的最大字符数


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


class FeishuMCPClient:
    """飞书 MCP 客户端"""
    
    def __init__(self):
        self._request_id = 0
    
    def _get_next_id(self) -> int:
        """获取下一个请求 ID"""
        self._request_id += 1
        return self._request_id
    
    def _get_headers(self) -> Dict[str, str]:
        """获取 MCP 请求头"""
        token = get_user_access_token()
        if not token:
            raise Exception("未获取到有效的 user_access_token，请先完成 OAuth 授权")
        
        return {
            "Content-Type": "application/json",
            "X-Lark-MCP-UAT": token,
            "X-Lark-MCP-Allowed-Tools": MCP_ALLOWED_TOOLS
        }
    
    def _call_mcp(self, method: str, params: Dict = None) -> Dict[str, Any]:
        """
        调用 MCP 服务
        
        Args:
            method: MCP 方法名 (initialize, tools/list, tools/call)
            params: 请求参数
            
        Returns:
            响应结果
        """
        headers = self._get_headers()
        
        payload = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": method
        }
        
        if params:
            payload["params"] = params
        
        logger.info(f"📡 MCP 请求: method={method}")
        
        try:
            response = requests.post(
                FEISHU_MCP_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
            result = response.json()
            
            # 检查错误
            if "error" in result:
                error = result["error"]
                logger.error(f"❌ MCP 错误: code={error.get('code')}, msg={error.get('message')}")
                return None
            
            return result.get("result", {})
            
        except Exception as e:
            logger.error(f"❌ MCP 请求失败: {e}")
            return None
    
    def initialize(self) -> bool:
        """初始化 MCP 连接"""
        result = self._call_mcp("initialize")
        if result:
            logger.info(f"✅ MCP 初始化成功: {result.get('serverInfo', {})}")
            return True
        return False
    
    def search_doc(self, query: str) -> Optional[Dict[str, Any]]:
        """
        搜索文档
        
        Args:
            query: 搜索关键词
            
        Returns:
            搜索结果
        """
        result = self._call_mcp("tools/call", {
            "name": "search-doc",
            "arguments": {
                "query": query
            }
        })
        
        if result:
            # 打印原始响应用于调试
            logger.info(f"📝 MCP 原始响应: {json.dumps(result, ensure_ascii=False)[:500]}")
            
            # 解析 MCP 返回的内容
            content_list = result.get("content", [])
            if content_list and len(content_list) > 0:
                text_content = content_list[0].get("text", "")
                logger.info(f"📝 MCP 文本内容: {text_content[:500]}")
                try:
                    return json.loads(text_content)
                except json.JSONDecodeError:
                    return {"raw": text_content}
        
        return None
    
    def fetch_doc(self, doc_id: str) -> Optional[str]:
        """
        获取文档内容
        
        Args:
            doc_id: 文档 ID
            
        Returns:
            文档内容
        """
        result = self._call_mcp("tools/call", {
            "name": "fetch-doc",
            "arguments": {
                "docID": doc_id
            }
        })
        
        if result:
            # 检查是否有错误
            if result.get("isError"):
                content_list = result.get("content", [])
                if content_list:
                    error_text = content_list[0].get("text", "")
                    logger.error(f"❌ 获取文档失败: {error_text}")
                return None
            
            # 解析内容
            content_list = result.get("content", [])
            if content_list and len(content_list) > 0:
                text_content = content_list[0].get("text", "")
                try:
                    data = json.loads(text_content)
                    return data.get("content", text_content)
                except json.JSONDecodeError:
                    return text_content
        
        return None


class FeishuDocsManager:
    """飞书文档管理器（使用 MCP 服务）"""
    
    def __init__(self, max_content_length: int = MAX_CONTENT_LENGTH):
        self.max_content_length = max_content_length
        self.mcp_client = FeishuMCPClient()
    
    def search_documents(self, query: str, count: int = DEFAULT_SEARCH_COUNT, 
                        doc_types: List[str] = None) -> List[SearchResult]:
        """
        搜索飞书文档（使用 MCP 服务）
        
        Args:
            query: 搜索关键词
            count: 返回结果数量
            doc_types: 文档类型过滤（MCP 暂不支持）
            
        Returns:
            搜索结果列表
        """
        if not is_user_authorized():
            logger.warning("⚠️ 用户未授权，无法搜索文档")
            return []
        
        logger.info(f"🔍 使用 MCP 搜索飞书文档: '{query}'")
        
        try:
            # 调用 MCP search-doc 工具
            result = self.mcp_client.search_doc(query)
            
            if not result:
                logger.info(f"📚 MCP 搜索无结果")
                return []
            
            # 解析搜索结果
            search_results = []
            
            # MCP 返回的数据结构可能是 docs 列表
            docs = result.get("docs", result.get("data", {}).get("docs", []))
            if isinstance(docs, list):
                for doc in docs[:count]:
                    search_results.append(SearchResult(
                        doc_token=doc.get("doc_token", doc.get("docToken", doc.get("token", ""))),
                        doc_type=doc.get("doc_type", doc.get("docType", "docx")),
                        title=doc.get("title", "未知标题"),
                        url=doc.get("url", doc.get("doc_url", "")),
                        owner_name=doc.get("owner_name", doc.get("owner", "")),
                        create_time=str(doc.get("create_time", "")),
                        update_time=str(doc.get("update_time", ""))
                    ))
            
            logger.info(f"✅ MCP 搜索到 {len(search_results)} 个文档")
            return search_results
            
        except Exception as e:
            logger.error(f"❌ MCP 搜索失败: {e}")
            return []
    
    def get_document_content(self, doc_token: str, doc_type: str = "docx") -> Optional[DocumentContent]:
        """
        获取文档内容（使用 MCP 服务）
        
        Args:
            doc_token: 文档 Token
            doc_type: 文档类型
            
        Returns:
            文档内容对象
        """
        if not is_user_authorized():
            logger.warning("⚠️ 用户未授权，无法获取文档内容")
            return None
        
        logger.info(f"📄 使用 MCP 获取文档内容: {doc_token}")
        
        try:
            # 调用 MCP fetch-doc 工具
            content = self.mcp_client.fetch_doc(doc_token)
            
            if not content:
                logger.info(f"📚 MCP 获取文档内容失败")
                return None
            
            # 清洗和截断内容
            cleaned_content, truncated, original_length = self._clean_and_truncate(content)
            
            return DocumentContent(
                doc_token=doc_token,
                title="",
                content=cleaned_content,
                doc_type=doc_type,
                url="",
                truncated=truncated,
                original_length=original_length
            )
            
        except Exception as e:
            logger.error(f"❌ MCP 获取文档失败: {e}")
            return None
    
    def _clean_and_truncate(self, content: str) -> tuple:
        """
        清洗和截断文档内容
        
        Args:
            content: 原始内容
            
        Returns:
            (清洗后的内容, 是否被截断, 原始长度)
        """
        if not content:
            return "", False, 0
        
        original_length = len(content)
        
        # 清洗内容
        # 1. 移除多余的空白字符
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r' {2,}', ' ', content)
        
        # 2. 移除可能的 JSON 标记或特殊字符
        content = re.sub(r'\u200b', '', content)  # 零宽空格
        
        # 3. 截断到最大长度
        truncated = False
        if len(content) > self.max_content_length:
            # 尝试在句子边界截断
            truncate_pos = self.max_content_length
            
            # 查找最近的句号、换行符
            for delimiter in ['\n\n', '。\n', '。', '\n', '；', '！', '？']:
                pos = content.rfind(delimiter, 0, self.max_content_length)
                if pos > self.max_content_length * 0.8:
                    truncate_pos = pos + len(delimiter)
                    break
            
            content = content[:truncate_pos]
            content += "\n\n...(内容已截断)"
            truncated = True
        
        return content.strip(), truncated, original_length
    
    def search_and_retrieve(self, query: str, count: int = DEFAULT_SEARCH_COUNT) -> List[DocumentContent]:
        """
        搜索并获取文档内容（一站式方法）
        
        Args:
            query: 搜索关键词
            count: 返回文档数量
            
        Returns:
            文档内容列表
        """
        # 1. 搜索文档
        search_results = self.search_documents(query, count)
        
        if not search_results:
            logger.info(f"未搜索到与 '{query}' 相关的文档")
            return []
        
        # 2. 获取每个文档的内容
        documents = []
        for result in search_results:
            content = self.get_document_content(result.doc_token, result.doc_type)
            if content:
                # 填充搜索结果中的信息
                content.title = result.title
                content.url = result.url
                documents.append(content)
        
        logger.info(f"✅ 成功获取 {len(documents)} 个文档内容")
        return documents
    
    def format_for_llm(self, documents: List[DocumentContent]) -> str:
        """
        将文档内容格式化为 LLM 可用的上下文
        
        Args:
            documents: 文档内容列表
            
        Returns:
            格式化后的文本
        """
        if not documents:
            return "未找到相关文档。"
        
        formatted_parts = ["📚 **检索到的飞书文档内容：**\n"]
        
        for i, doc in enumerate(documents, 1):
            truncate_hint = " (内容已截断)" if doc.truncated else ""
            doc_type_name = DOC_TYPE_MAP.get(doc.doc_type, doc.doc_type)
            
            part = f"""
---
### 📄 文档 {i}: {doc.title}
- 类型: {doc_type_name}
- 链接: {doc.url}
{truncate_hint}

**内容:**
{doc.content}
"""
            formatted_parts.append(part)
        
        formatted_parts.append("\n---\n以上是检索到的文档内容，请基于这些信息回答用户问题。")
        
        return "\n".join(formatted_parts)


# 全局单例实例
_docs_manager: Optional[FeishuDocsManager] = None


def get_docs_manager() -> FeishuDocsManager:
    """获取全局文档管理器实例"""
    global _docs_manager
    if _docs_manager is None:
        _docs_manager = FeishuDocsManager()
    return _docs_manager


def search_feishu_knowledge(query: str, count: int = 3) -> str:
    """
    搜索飞书知识库（供 LLM Function Calling 使用）
    
    Args:
        query: 搜索关键词
        count: 返回文档数量
        
    Returns:
        格式化的文档内容字符串
    """
    manager = get_docs_manager()
    
    # 检查授权状态
    if not is_user_authorized():
        return "⚠️ 飞书文档检索功能未授权。请管理员先完成 OAuth 授权流程。"
    
    try:
        # 搜索并获取文档
        documents = manager.search_and_retrieve(query, count)
        
        # 格式化返回
        return manager.format_for_llm(documents)
        
    except Exception as e:
        logger.error(f"搜索飞书文档失败: {e}")
        return f"❌ 搜索飞书文档时发生错误: {str(e)}"


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("📚 飞书文档检索模块测试")
    print("=" * 60)
    
    # 检查授权状态
    if not is_user_authorized():
        print("\n⚠️ 用户未授权，请先运行 feishu_auth.py 完成 OAuth 授权")
        print("   python3 feishu_auth.py")
        exit(1)
    
    # 测试搜索
    test_query = input("\n请输入搜索关键词 (默认: 测试): ") or "测试"
    
    print(f"\n正在搜索: '{test_query}'...")
    result = search_feishu_knowledge(test_query)
    
    print("\n" + "=" * 60)
    print("搜索结果:")
    print("=" * 60)
    print(result)
