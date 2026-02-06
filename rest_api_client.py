#!/usr/bin/env python3
"""
飞书 REST API 客户端（不使用 MCP，直接调用 HTTP API）
解决 Railway 内存不足问题
"""

import os
import json
import logging
import requests
from typing import Optional, Dict, Any, List
from feishu_auth import get_user_access_token

logger = logging.getLogger(__name__)

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")


def _get_app_access_token() -> Optional[str]:
    """获取应用级别的 access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal"
    
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        
        if result.get("code") == 0:
            return result.get("app_access_token")
        else:
            logger.error(f"获取 app_access_token 失败: {result.get('msg')}")
            return None
    except Exception as e:
        logger.error(f"请求 app_access_token 失败: {e}")
        return None


def search_feishu_docs_rest(query: str, count: int = 3) -> str:
    """
    使用 REST API 搜索飞书文档
    
    Args:
        query: 搜索关键词
        count: 返回文档数量
        
    Returns:
        格式化的搜索结果
    """
    logger.info(f"🔍 [REST API] 搜索飞书文档: '{query}'")
    
    # 获取用户 access_token
    user_token = get_user_access_token()
    if not user_token:
        logger.error("❌ 未获取到用户 access_token")
        return "❌ 未授权。请先完成 OAuth 授权。"
    
    # 调用飞书搜索 API
    url = "https://open.feishu.cn/open-apis/search/v1/docs"
    
    headers = {
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "query": query,
        "page_size": count
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        # 调试：记录原始响应
        logger.debug(f"响应状态码: {response.status_code}")
        logger.debug(f"响应内容: {response.text[:500]}")
        
        # 检查响应状态码
        if response.status_code != 200:
            logger.error(f"❌ HTTP 错误: {response.status_code}, 内容: {response.text[:200]}")
            return f"❌ 搜索文档失败: HTTP {response.status_code}"
        
        # 尝试解析 JSON
        try:
            result = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 解析失败: {e}, 响应内容: {response.text[:200]}")
            return f"❌ 搜索文档失败: 响应格式错误"
        
        if result.get("code") != 0:
            error_msg = result.get("msg", "未知错误")
            logger.error(f"❌ 搜索文档失败: {error_msg}")
            return f"❌ 搜索文档失败: {error_msg}"
        
        data = result.get("data", {})
        docs = data.get("docs", [])
        
        if not docs:
            logger.info(f"ℹ️  未找到与 '{query}' 相关的文档")
            return f"未找到与 '{query}' 相关的飞书文档。"
        
        # 格式化结果
        formatted_parts = [f"📚 **检索到的飞书文档内容：**\n\n找到 {len(docs)} 个相关文档：\n"]
        
        for i, doc in enumerate(docs, 1):
            title = doc.get("title", "无标题")
            doc_type = doc.get("doc_type", "docx")
            url = doc.get("url", "")
            owner_name = doc.get("owner_name", "")
            
            part = f"""
---
### 📄 文档 {i}: {title}
- 类型: {doc_type}
- 链接: {url}
- 作者: {owner_name}
"""
            formatted_parts.append(part)
        
        formatted_parts.append("\n---\n以上是检索到的飞书文档内容，请基于这些信息回答用户问题。")
        
        result_text = "\n".join(formatted_parts)
        logger.info(f"✅ [REST API] 搜索成功，找到 {len(docs)} 个文档")
        return result_text
        
    except requests.exceptions.Timeout:
        logger.error("❌ 搜索文档超时")
        return "❌ 搜索文档超时，请稍后重试。"
    except Exception as e:
        logger.error(f"❌ 搜索文档异常: {e}")
        return f"❌ 搜索文档失败: {str(e)}"


# 兼容旧接口
def search_feishu_knowledge_real(query: str, count: int = 3) -> str:
    """兼容接口，使用 REST API"""
    return search_feishu_docs_rest(query, count)


if __name__ == "__main__":
    # 测试
    logging.basicConfig(level=logging.INFO)
    result = search_feishu_docs_rest("入库", 3)
    print(result)
