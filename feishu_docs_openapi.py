#!/usr/bin/env python3
"""
飞书云文档检索模块（OpenAPI 方式）
使用飞书 OpenAPI MCP 实现文档搜索和内容获取
"""

import os
import re
import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 尝试导入真实客户端，如果失败则回退到简单客户端
# 优先使用 REST API 方式（不需要 Node.js，解决 Railway 内存问题）
try:
    from rest_api_client import search_feishu_knowledge_real
    HAS_REAL_CLIENT = True
    logger.info("✅ 使用 REST API 客户端（无 Node.js 内存占用）")
except ImportError as e:
    logger.warning(f"⚠️  无法导入 REST API 客户端: {e}")
    # 尝试使用旧的 MCP 客户端
    try:
        from real_openapi_client import search_feishu_knowledge_real
        HAS_REAL_CLIENT = True
        logger.info("✅ 使用 OpenAPI MCP 客户端")
    except ImportError:
        HAS_REAL_CLIENT = False
        logger.warning("⚠️  无法导入 OpenAPI 客户端，使用简单客户端")
        from simple_openapi_client import search_feishu_knowledge_simple

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

class FeishuOpenAPIDocsManager:
    """飞书 OpenAPI 文档管理器"""
    
    def __init__(self, max_content_length: int = MAX_CONTENT_LENGTH):
        self.max_content_length = max_content_length
    
    def search_documents(self, query: str, count: int = DEFAULT_SEARCH_COUNT) -> List[SearchResult]:
        """
        搜索飞书文档（使用 OpenAPI 方式）
        """
        logger.info(f"🔍 使用 OpenAPI 搜索飞书文档: '{query}'")
        
        try:
            # 使用简化版客户端进行搜索
            result_text = search_feishu_knowledge_simple(query, count)
            
            # 解析结果文本，提取文档信息
            search_results = []
            
            # 简单解析 - 从格式化文本中提取文档信息
            if "未找到相关文档" not in result_text:
                # 这里可以根据实际返回格式进行解析
                # 暂时返回模拟结果
                search_results.append(SearchResult(
                    doc_token="test_doc_token",
                    doc_type="docx",
                    title=f"搜索结果: {query}",
                    url="https://k7ftx11633c.feishu.cn/docx/test_doc_token"
                ))
            
            logger.info(f"✅ OpenAPI 搜索到 {len(search_results)} 个文档")
            return search_results
            
        except Exception as e:
            logger.error(f"❌ OpenAPI 文档搜索失败: {e}")
            return []
    
    def get_document_content(self, doc_token: str, doc_type: str = "docx") -> Optional[DocumentContent]:
        """
        获取文档内容（使用 OpenAPI 方式）
        """
        logger.info(f"📄 使用 OpenAPI 获取文档内容: {doc_token}")
        
        try:
            # 使用简化版客户端获取内容
            result_text = search_feishu_knowledge_simple(doc_token, 1)
            
            if "未找到相关文档" in result_text:
                return None
            
            # 清洗和截断内容
            cleaned_content, truncated, original_length = self._clean_and_truncate(result_text)
            
            return DocumentContent(
                doc_token=doc_token,
                title=f"文档: {doc_token}",
                content=cleaned_content,
                doc_type=doc_type,
                url=f"https://k7ftx11633c.feishu.cn/docx/{doc_token}",
                truncated=truncated,
                original_length=original_length
            )
            
        except Exception as e:
            logger.error(f"❌ OpenAPI 获取文档失败: {e}")
            return None
    
    def _clean_and_truncate(self, content: str) -> tuple:
        """清洗和截断文档内容"""
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
        """搜索并获取文档内容（一站式方法）"""
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
        """将文档内容格式化为 LLM 可用的上下文"""
        if not documents:
            return "未找到相关文档。"
        
        formatted_parts = ["📚 **检索到的飞书文档内容：**\n"]
        
        for i, doc in enumerate(documents, 1):
            truncate_hint = " (内容已截断)" if doc.truncated else ""
            doc_type_name = "文档"  # 简化处理
            
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
_docs_manager: Optional[FeishuOpenAPIDocsManager] = None

def get_docs_manager() -> FeishuOpenAPIDocsManager:
    """获取全局文档管理器实例"""
    global _docs_manager
    if _docs_manager is None:
        _docs_manager = FeishuOpenAPIDocsManager()
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
    # 优先使用真实客户端
    if HAS_REAL_CLIENT:
        try:
            logger.info(f"🔍 使用真实 OpenAPI 客户端搜索: '{query}'")
            return search_feishu_knowledge_real(query, count)
        except Exception as e:
            logger.error(f"真实客户端搜索失败: {e}")
            # 回退到简单客户端
            pass
    
    # 使用简单客户端或回退
    try:
        logger.info(f"🔍 使用简单 OpenAPI 客户端搜索: '{query}'")
        return search_feishu_knowledge_simple(query, count)
    except Exception as e:
        logger.error(f"搜索飞书文档失败: {e}")
        return f"❌ 搜索飞书文档时发生错误: {str(e)}"

# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("📚 飞书文档检索模块测试 (OpenAPI 方式)")
    print("=" * 60)
    
    # 测试搜索
    test_query = input("\n请输入搜索关键词 (默认: 测试): ") or "测试"
    
    print(f"\n正在搜索: '{test_query}'...")
    result = search_feishu_knowledge(test_query)
    
    print("\n" + "=" * 60)
    print("搜索结果:")
    print("=" * 60)
    print(result)