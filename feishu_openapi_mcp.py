#!/usr/bin/env python3
"""
飞书 OpenAPI MCP 客户端
使用本地 OpenAPI MCP 服务实现文档搜索和内容获取
"""

import os
import re
import json
import logging
import subprocess
import threading
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_SEARCH_COUNT = 3
MAX_CONTENT_LENGTH = 4000

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

class FeishuOpenAPIMCPClient:
    """飞书 OpenAPI MCP 客户端"""
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.process: Optional[subprocess.Popen] = None
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
                    "--oauth"
                ]
                
                # 启动进程
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
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
    
    def search_documents(self, query: str, count: int = DEFAULT_SEARCH_COUNT) -> List[SearchResult]:
        """
        搜索文档（使用 OpenAPI wiki.v1.node.search）
        
        Args:
            query: 搜索关键词
            count: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        if not self.start_mcp_service():
            return []
        
        try:
            logger.info(f"🔍 使用 OpenAPI 搜索文档: '{query}'")
            
            # 使用 wiki.v1.node.search API 搜索知识库文档
            # 这里需要构造正确的 JSON-RPC 请求
            logger.info("🚧 OpenAPI 搜索功能正在开发中...")
            logger.info("将使用 wiki.v1.node.search API 实现文档搜索")
            return []
            
        except Exception as e:
            logger.error(f"❌ OpenAPI 文档搜索失败: {e}")
            return []

    def get_document_content(self, doc_token: str) -> Optional[DocumentContent]:
        """
        获取文档内容（使用 OpenAPI docx.v1.document.rawContent）
        
        Args:
            doc_token: 文档 Token
            
        Returns:
            文档内容对象
        """
        if not self.start_mcp_service():
            return None
        
        try:
            logger.info(f"📄 使用 OpenAPI 获取文档内容: {doc_token}")
            
            # 使用 docx.v1.document.rawContent API 获取文档内容
            # 这里需要构造正确的 JSON-RPC 请求
            logger.info("🚧 OpenAPI 文档获取功能正在开发中...")
            logger.info("将使用 docx.v1.document.rawContent API 获取文档内容")
            return None
            
        except Exception as e:
            logger.error(f"❌ OpenAPI 获取文档内容失败: {e}")
            return None

class FeishuOpenAPIDocsManager:
    """飞书 OpenAPI 文档管理器"""
    
    def __init__(self, app_id: str, app_secret: str, max_content_length: int = MAX_CONTENT_LENGTH):
        self.max_content_length = max_content_length
        self.mcp_client = FeishuOpenAPIMCPClient(app_id, app_secret)
    
    def search_documents(self, query: str, count: int = DEFAULT_SEARCH_COUNT) -> List[SearchResult]:
        """搜索文档"""
        return self.mcp_client.search_documents(query, count)
    
    def get_document_content(self, doc_token: str) -> Optional[DocumentContent]:
        """获取文档内容"""
        return self.mcp_client.get_document_content(doc_token)
    
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
    """
    使用 OpenAPI MCP 搜索飞书知识库
    
    Args:
        query: 搜索关键词
        count: 返回文档数量
        
    Returns:
        格式化的文档内容字符串
    """
    try:
        manager = get_openapi_docs_manager()
        documents = manager.search_and_retrieve(query, count)
        return manager.format_for_llm(documents)
    except Exception as e:
        logger.error(f"OpenAPI 搜索失败: {e}")
        return f"❌ OpenAPI 搜索失败: {str(e)}"

# 程序退出时清理资源
import atexit
atexit.register(lambda: [manager.mcp_client.stop_mcp_service() for manager in _managers.values()])