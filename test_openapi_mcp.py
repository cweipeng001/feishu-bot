#!/usr/bin/env python3
"""
测试 OpenAPI MCP 功能
"""

import os
import json
from dotenv import load_dotenv
from feishu_openapi_mcp import get_openapi_docs_manager, search_feishu_knowledge_openapi

def test_openapi_mcp():
    """测试 OpenAPI MCP 基本功能"""
    print("=" * 60)
    print("🧪 OpenAPI MCP 功能测试")
    print("=" * 60)
    
    # 加载环境变量
    load_dotenv()
    
    try:
        # 获取文档管理器
        manager = get_openapi_docs_manager()
        print("✅ 成功创建 OpenAPI 文档管理器")
        
        # 测试搜索功能
        print("\n🔍 测试文档搜索功能...")
        result = search_feishu_knowledge_openapi("测试", 1)
        print("搜索结果:")
        print(result)
        
        print("\n✅ OpenAPI MCP 测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_openapi_mcp()