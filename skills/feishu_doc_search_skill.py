#!/usr/bin/env python3
"""
飞书文档搜索 Skill
封装飞书知识库文档搜索功能
"""

import logging
from typing import Dict, Any
from feishu_docs_openapi import search_feishu_knowledge
from feishu_auth import is_user_authorized

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def feishu_doc_search_skill(query: str, count: int = 3) -> Dict[str, Any]:
    """
    飞书文档搜索 Skill
    
    Args:
        query: 搜索关键词
        count: 返回文档数量，默认 3
        
    Returns:
        {
            "success": bool,
            "result": str,  # 格式化的搜索结果
            "error": str,   # 错误信息（如果有）
            "documents_found": int  # 找到的文档数量
        }
    """
    logger.info(f"📚 [Skill] 飞书文档搜索: query='{query}', count={count}")
    
    # 检查授权状态
    if not is_user_authorized():
        logger.warning("⚠️  [Skill] 用户未授权")
        return {
            "success": False,
            "result": "",
            "error": "未授权。请先访问 /auth/feishu 完成 OAuth 授权。",
            "documents_found": 0
        }
    
    try:
        # 调用文档搜索
        result = search_feishu_knowledge(query, count)
        
        # 判断是否成功
        if "未找到" in result or "未授权" in result or "错误" in result:
            logger.info(f"ℹ️  [Skill] 未找到相关文档")
            return {
                "success": False,
                "result": result,
                "error": "未找到相关文档",
                "documents_found": 0
            }
        
        # 统计找到的文档数量
        doc_count = result.count("### 📄 文档")
        
        logger.info(f"✅ [Skill] 搜索成功，找到 {doc_count} 个文档")
        return {
            "success": True,
            "result": result,
            "error": "",
            "documents_found": doc_count
        }
        
    except Exception as e:
        logger.error(f"❌ [Skill] 搜索失败: {e}")
        return {
            "success": False,
            "result": "",
            "error": str(e),
            "documents_found": 0
        }

# Skill 元数据
SKILL_METADATA = {
    "name": "feishu-doc-search",
    "description": "搜索飞书知识库文档",
    "handler": feishu_doc_search_skill,
    "params_schema": {
        "query": {
            "type": "string",
            "required": True,
            "description": "搜索关键词"
        },
        "count": {
            "type": "integer",
            "required": False,
            "default": 3,
            "description": "返回文档数量"
        }
    },
    "enabled": True
}

# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 飞书文档搜索 Skill 测试")
    print("=" * 60)
    
    # 测试搜索
    test_query = input("\n请输入搜索关键词 (默认: 测试): ") or "测试"
    
    result = feishu_doc_search_skill(query=test_query, count=3)
    
    print("\n" + "=" * 60)
    print("搜索结果:")
    print("=" * 60)
    print(f"成功: {result['success']}")
    print(f"找到文档数: {result['documents_found']}")
    if result['error']:
        print(f"错误: {result['error']}")
    print(f"\n{result['result']}")
