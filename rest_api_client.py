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


def optimize_search_query(query: str) -> str:
    """
    优化搜索关键词，提高搜索命中率
    
    Args:
        query: 原始搜索关键词
        
    Returns:
        优化后的搜索关键词
    """
    # 移除常见的搜索前缀
    prefixes = ["搜索", "查找", "查询", "帮我查", "找一下"]
    optimized = query.lower().strip()
    
    for prefix in prefixes:
        if optimized.startswith(prefix):
            optimized = optimized[len(prefix):].strip()
            break
    
    # 添加相关的同义词和扩展词
    synonyms_map = {
        "入库": ["入库", "进货", "采购", "仓储"],
        "文档": ["文档", "文件", "资料", "记录", "报告"],
        "项目": ["项目", "工程", "任务", "计划"],
        "技术": ["技术", "科技", "开发", "研发"],
        "产品": ["产品", "商品", "服务", "解决方案"]
    }
    
    # 如果查询词较短，尝试扩展
    if len(optimized) <= 4:
        for key, synonyms in synonyms_map.items():
            if key in optimized:
                # 返回多个可能的搜索词
                return " OR ".join(synonyms)
    
    return optimized

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
    
    # 优化搜索关键词
    optimized_query = optimize_search_query(query)
    logger.info(f"🔍 [REST API] 原始搜索: '{query}' -> 优化后: '{optimized_query}'")
    
    # 获取用户 access_token
    user_token = get_user_access_token()
    if not user_token:
        logger.error("❌ 未获取到用户 access_token")
        return "❌ 未授权。请先完成 OAuth 授权。"
    
    # 使用新版 Drive API 搜索文档
    # 参考: https://open.feishu.cn/document/server-docs/docs/drive-v1/search/document-search
    url = "https://open.feishu.cn/open-apis/drive/v1/files/search"
    
    headers = {
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json"
    }
    
    # 获取用户信息用于搜索
    from feishu_auth import get_auth_manager
    auth_manager = get_auth_manager()
    user_info = auth_manager.get_user_info()
    user_id = user_info.get('open_id') if user_info else None
    
    # POST 请求体 - 飞书 Drive API 正确参数格式
    payload = {
        "search_key": optimized_query,
        "count": count,
        "offset": 0
        # 移除 docs_types 参数，让 API 使用默认值以避免验证错误
    }
    
    # 如果有用户ID，添加到请求中
    if user_id:
        payload["user_id"] = user_id
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        # 调试：记录原始响应
        logger.debug(f"响应状态码: {response.status_code}")
        logger.debug(f"响应内容: {response.text[:1000]}")
        
        # 特别记录搜索相关的调试信息
        logger.info(f"🔍 [调试] 搜索请求详情:")
        logger.info(f"   URL: {url}")
        logger.info(f"   Headers: {{'Authorization': 'Bearer ***{user_token[-10:] if user_token else 'None'}', 'Content-Type': 'application/json'}}")
        logger.info(f"   Payload: {payload}")
        
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
        # drive/v1/files/search 返回的是 files 或 docs_entities
        docs = data.get("files", []) or data.get("docs_entities", []) or data.get("docs", [])
        
        # 详细记录搜索结果
        logger.info(f"🔍 [调试] 搜索结果分析:")
        logger.info(f"   原始数据结构: {list(data.keys()) if isinstance(data, dict) else '非字典类型'}")
        logger.info(f"   files 字段: {len(data.get('files', []))} 项")
        logger.info(f"   docs_entities 字段: {len(data.get('docs_entities', []))} 项")
        logger.info(f"   docs 字段: {len(data.get('docs', []))} 项")
        logger.info(f"   最终匹配文档数: {len(docs)} 项")
        
        if not docs:
            logger.info(f"ℹ️  未找到与 '{query}' 相关的文档")
            return f"未找到与 '{query}' 相关的飞书文档。"
        
        # 格式化结果
        formatted_parts = [f"📚 **检索到的飞书文档内容：**\n\n找到 {len(docs)} 个相关文档：\n"]
        
        for i, doc in enumerate(docs, 1):
            # 适配不同 API 的字段名称
            title = doc.get("title", "") or doc.get("name", "") or doc.get("docs_token", "无标题")
            doc_type = doc.get("type", "") or doc.get("docs_type", "") or doc.get("doc_type", "docx")
            doc_token = doc.get("token", "") or doc.get("docs_token", "")
            doc_url = doc.get("url", "") or f"https://k7ftx11633c.feishu.cn/{doc_type}/{doc_token}"
            owner_name = doc.get("owner", {}).get("name", "") if isinstance(doc.get("owner"), dict) else doc.get("owner_name", "")
            
            part = f"""
---
### 📄 文档 {i}: {title}
- 类型: {doc_type}
- 链接: {doc_url}
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
