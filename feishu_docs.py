#!/usr/bin/env python3
"""
飞书云文档检索模块
提供文档搜索、内容获取和文本处理功能
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

# 飞书 API 端点
FEISHU_DOC_SEARCH_URL = "https://open.feishu.cn/open-apis/suite/docs-api/search/object"
FEISHU_DOCX_CONTENT_URL = "https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/raw_content"
FEISHU_DOC_CONTENT_URL = "https://open.feishu.cn/open-apis/doc/v2/{document_id}/raw_content"
FEISHU_WIKI_SEARCH_URL = "https://open.feishu.cn/open-apis/wiki/v2/spaces/search"

# 文档类型映射
DOC_TYPE_MAP = {
    "doc": "旧版文档",
    "docx": "新版文档",
    "sheet": "电子表格",
    "bitable": "多维表格",
    "mindnote": "思维笔记",
    "wiki": "知识库",
    "file": "文件",
    "slide": "幻灯片"
}

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


class FeishuDocsManager:
    """飞书文档管理器"""
    
    def __init__(self, max_content_length: int = MAX_CONTENT_LENGTH):
        """
        初始化文档管理器
        
        Args:
            max_content_length: 返回内容的最大字符数
        """
        self.max_content_length = max_content_length
    
    def _get_headers(self) -> Dict[str, str]:
        """获取 API 请求头（包含 user_access_token）"""
        token = get_user_access_token()
        if not token:
            raise Exception("未获取到有效的 user_access_token，请先完成 OAuth 授权")
        
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def search_documents(self, query: str, count: int = DEFAULT_SEARCH_COUNT, 
                        doc_types: List[str] = None) -> List[SearchResult]:
        """
        搜索飞书文档
        
        Args:
            query: 搜索关键词
            count: 返回结果数量
            doc_types: 文档类型过滤，如 ["docx", "doc", "wiki"]
            
        Returns:
            搜索结果列表
        """
        if not is_user_authorized():
            logger.warning("⚠️ 用户未授权，无法搜索文档")
            return []
        
        logger.info(f"🔍 搜索飞书文档: '{query}'")
        
        # 构建搜索请求
        payload = {
            "search_key": query,
            "count": count,
            "offset": 0,
            "owner_ids": [],
            "chat_ids": [],
            "docs_types": doc_types or ["docx", "doc", "wiki"]
        }
        
        try:
            headers = self._get_headers()
            response = requests.post(
                FEISHU_DOC_SEARCH_URL,
                json=payload,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                error_msg = result.get("msg", "未知错误")
                logger.error(f"搜索文档失败: {error_msg}")
                return []
            
            # 解析搜索结果
            docs_data = result.get("data", {}).get("docs_entities", [])
            search_results = []
            
            for doc in docs_data:
                search_results.append(SearchResult(
                    doc_token=doc.get("docs_token", ""),
                    doc_type=doc.get("docs_type", ""),
                    title=doc.get("title", "未知标题"),
                    url=doc.get("url", ""),
                    owner_name=doc.get("owner", {}).get("name", ""),
                    create_time=doc.get("create_time", ""),
                    update_time=doc.get("update_time", "")
                ))
            
            logger.info(f"✅ 搜索到 {len(search_results)} 个文档")
            return search_results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"搜索文档请求失败: {e}")
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
        if not is_user_authorized():
            logger.warning("⚠️ 用户未授权，无法获取文档内容")
            return None
        
        logger.info(f"📄 获取文档内容: {doc_token} (类型: {doc_type})")
        
        # 根据文档类型选择 API
        if doc_type == "docx":
            url = FEISHU_DOCX_CONTENT_URL.format(document_id=doc_token)
        elif doc_type == "doc":
            url = FEISHU_DOC_CONTENT_URL.format(document_id=doc_token)
        else:
            logger.warning(f"⚠️ 暂不支持获取 {doc_type} 类型文档的内容")
            return None
        
        try:
            headers = self._get_headers()
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                error_msg = result.get("msg", "未知错误")
                logger.error(f"获取文档内容失败: {error_msg}")
                return None
            
            # 提取内容
            content = result.get("data", {}).get("content", "")
            
            # 清洗和截断内容
            cleaned_content, truncated, original_length = self._clean_and_truncate(content)
            
            return DocumentContent(
                doc_token=doc_token,
                title="",  # 标题需要从搜索结果中获取
                content=cleaned_content,
                doc_type=doc_type,
                url="",
                truncated=truncated,
                original_length=original_length
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取文档内容请求失败: {e}")
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
