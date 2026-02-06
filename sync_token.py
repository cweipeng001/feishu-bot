#!/usr/bin/env python3
"""
一键同步 Token 到 Railway
通过 GitHub Actions 自动化同步
"""

import json
import os
import sys
import webbrowser

TOKEN_FILE = "feishu_user_token.json"

def main():
    print("\n🚀 一键同步飞书 Token 到 Railway")
    print("=" * 80)
    
    # 检查 Token 文件
    if not os.path.exists(TOKEN_FILE):
        print(f"❌ 错误: 找不到 {TOKEN_FILE}")
        print("请先运行: python3 get_token.py")
        sys.exit(1)
    
    with open(TOKEN_FILE, 'r') as f:
        token_data = json.load(f)
    
    print("✅ 读取 Token 文件成功\n")
    
    # 方案 1: 手动复制到 Railway (最快)
    print("📋 方案 1: 手动配置 Railway (推荐，最快)")
    print("-" * 80)
    print("打开 Railway 项目设置 → Variables，添加/更新以下环境变量：\n")
    print(f"FEISHU_USER_ACCESS_TOKEN={token_data['access_token']}")
    print(f"FEISHU_USER_REFRESH_TOKEN={token_data['refresh_token']}")
    print(f"FEISHU_USER_TOKEN_SCOPE={token_data['scope']}")
    print(f"FEISHU_USER_TOKEN_OBTAINED_AT={token_data['obtained_at']}")
    print()
    
    # 方案 2: GitHub Actions 自动化
    print("🤖 方案 2: 通过 GitHub Actions 自动同步 (需配置)")
    print("-" * 80)
    print("1. 在 GitHub 仓库设置 Secrets: RAILWAY_TOKEN")
    print("2. 打开 Actions → Sync Feishu Token to Railway → Run workflow")
    print("3. 填入以下参数：")
    print(f"   - access_token: {token_data['access_token'][:30]}...")
    print(f"   - refresh_token: {token_data['refresh_token'][:30]}...")
    print(f"   - token_scope: {token_data['scope']}")
    print(f"   - obtained_at: {token_data['obtained_at']}")
    print()
    
    # 询问是否打开浏览器
    choice = input("选择操作:\n  1 - 复制后手动配置 Railway\n  2 - 打开 GitHub Actions 页面\n  q - 退出\n\n请选择 (1/2/q): ").strip()
    
    if choice == '1':
        print("\n✅ 环境变量已在上方显示，请手动复制到 Railway")
        print("Railway 项目地址: https://railway.app/")
    elif choice == '2':
        # 尝试打开 GitHub Actions 页面
        repo_url = "https://github.com/cweipeng001/feishu-bot/actions/workflows/sync-token.yml"
        print(f"\n🌐 正在打开: {repo_url}")
        webbrowser.open(repo_url)
    else:
        print("\n👋 已退出")
    
    print("\n" + "=" * 80)
    print("⚠️  注意:")
    print("  - access_token 有效期 2 小时，但 Railway 会自动刷新")
    print("  - refresh_token 有效期 30 天")
    print("  - 每次本地重新授权后，需要重新同步")
    print("=" * 80)

if __name__ == "__main__":
    main()
