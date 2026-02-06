#!/usr/bin/env python3
"""
自动同步飞书 Token 到 Railway
从本地 feishu_user_token.json 读取并自动推送到 Railway
"""

import json
import os
import subprocess
import sys

TOKEN_FILE = "feishu_user_token.json"

def check_railway_cli():
    """检查 Railway CLI 是否已安装"""
    try:
        result = subprocess.run(['railway', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Railway CLI 已安装: {result.stdout.strip()}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    print("❌ Railway CLI 未安装")
    print("\n请选择安装方式：")
    print("1. macOS/Linux: curl -fsSL https://railway.app/install.sh | sh")
    print("2. npm: npm install -g @railway/cli")
    print("3. 手动下载: https://railway.app/cli")
    return False

def check_railway_login():
    """检查是否已登录 Railway"""
    try:
        result = subprocess.run(['railway', 'whoami'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ 已登录 Railway: {result.stdout.strip()}")
            return True
        else:
            print("❌ 未登录 Railway")
            print("请运行: railway login")
            return False
    except Exception as e:
        print(f"❌ 检查登录状态失败: {e}")
        return False

def sync_to_railway(token_data, auto_confirm=False):
    """同步 Token 到 Railway"""
    env_vars = {
        "FEISHU_USER_ACCESS_TOKEN": token_data['access_token'],
        "FEISHU_USER_REFRESH_TOKEN": token_data['refresh_token'],
        "FEISHU_USER_TOKEN_SCOPE": token_data['scope'],
        "FEISHU_USER_TOKEN_OBTAINED_AT": str(token_data['obtained_at'])
    }
    
    print("\n" + "=" * 80)
    print("📤 准备同步以下环境变量到 Railway:")
    print("=" * 80)
    for key, value in env_vars.items():
        display_value = value if len(value) < 50 else value[:47] + "..."
        print(f"  {key}={display_value}")
    print("=" * 80)
    
    if not auto_confirm:
        confirm = input("\n确认同步到 Railway? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ 已取消同步")
            return False
    
    print("\n🚀 开始同步...")
    
    success_count = 0
    for key, value in env_vars.items():
        try:
            # 使用 railway variables --set 命令
            result = subprocess.run(
                ['railway', 'variables', '--set', f'{key}={value}'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                print(f"  ✅ {key}")
                success_count += 1
            else:
                print(f"  ❌ {key}: {result.stderr.strip()}")
        except Exception as e:
            print(f"  ❌ {key}: {e}")
    
    print("\n" + "=" * 80)
    if success_count == len(env_vars):
        print(f"✅ 成功同步 {success_count}/{len(env_vars)} 个环境变量")
        print("\n⚠️  Railway 将自动重新部署，请等待 2-3 分钟")
        return True
    else:
        print(f"⚠️  部分同步失败: {success_count}/{len(env_vars)} 成功")
        return False

def print_manual_config(token_data):
    """打印手动配置说明"""
    print("\n" + "=" * 80)
    print("📋 手动配置 Railway 环境变量")
    print("=" * 80)
    print("\n请在 Railway 项目设置中，添加/更新以下环境变量：\n")
    print(f"FEISHU_USER_ACCESS_TOKEN={token_data['access_token']}")
    print(f"FEISHU_USER_REFRESH_TOKEN={token_data['refresh_token']}")
    print(f"FEISHU_USER_TOKEN_SCOPE={token_data['scope']}")
    print(f"FEISHU_USER_TOKEN_OBTAINED_AT={token_data['obtained_at']}")
    print("\n" + "=" * 80)

def main():
    """主函数"""
    print("\n🔄 飞书 Token 自动同步到 Railway")
    print("=" * 80)
    
    # 1. 检查 Token 文件
    if not os.path.exists(TOKEN_FILE):
        print(f"❌ 错误: 找不到 {TOKEN_FILE}")
        print("请先运行: python3 get_token.py")
        sys.exit(1)
    
    with open(TOKEN_FILE, 'r') as f:
        token_data = json.load(f)
    
    print(f"✅ 读取 Token 文件成功")
    
    # 2. 检查 Railway CLI
    if not check_railway_cli():
        print("\n💡 提示: 安装 Railway CLI 后可自动同步")
        print_manual_config(token_data)
        sys.exit(1)
    
    # 3. 检查登录状态
    if not check_railway_login():
        print_manual_config(token_data)
        sys.exit(1)
    
    # 4. 同步到 Railway
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv
    success = sync_to_railway(token_data, auto_confirm)
    
    if success:
        print("\n⚠️  注意事项：")
        print("  1. access_token 有效期 2 小时")
        print("  2. refresh_token 有效期 30 天")
        print("  3. Railway 会自动使用 refresh_token 刷新")
        print("=" * 80)
    else:
        print("\n建议手动配置:")
        print_manual_config(token_data)

if __name__ == "__main__":
    main()
