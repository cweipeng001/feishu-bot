#!/usr/bin/env python3
"""
飞书机器人配置助手
帮助您快速配置飞书机器人与Qoder的集成
"""

import os
import sys
import subprocess


def print_header(text):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def check_python_version():
    """检查Python版本"""
    print("检查Python版本...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print(f"❌ Python版本过低: {version.major}.{version.minor}")
        print("   请使用Python 3.7或更高版本")
        return False
    print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
    return True


def check_dependencies():
    """检查依赖是否安装"""
    print("\n检查依赖包...")
    required_packages = ['flask', 'requests', 'python-dotenv']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} 已安装")
        except ImportError:
            print(f"❌ {package} 未安装")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n需要安装以下依赖包: {', '.join(missing_packages)}")
        install = input("是否现在安装？(y/n): ").lower()
        if install == 'y':
            print("\n正在安装依赖...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
                print("✅ 依赖安装完成")
                return True
            except subprocess.CalledProcessError:
                print("❌ 依赖安装失败，请手动执行: pip install -r requirements.txt")
                return False
        else:
            return False
    
    return True


def create_env_file():
    """创建.env配置文件"""
    print_header("创建环境配置文件")
    
    if os.path.exists(".env"):
        overwrite = input(".env文件已存在，是否覆盖？(y/n，默认: n): ").lower()
        if overwrite != 'y':
            print("跳过创建.env文件")
            return True
    
    print("\n请输入飞书机器人配置信息（可在飞书开放平台获取）：")
    print("官方地址: https://open.feishu.cn/app\n")
    
    app_id = input("App ID (例如: cli_a1b2c3d4e5f6): ").strip()
    app_secret = input("App Secret: ").strip()
    verification_token = input("Verification Token: ").strip()
    encrypt_key = input("Encrypt Key (可选，直接回车跳过): ").strip()
    
    print("\n请输入Qoder配置信息：")
    qoder_endpoint = input("Qoder API端点 (默认: http://localhost:8080/api/chat): ").strip() or "http://localhost:8080/api/chat"
    qoder_api_key = input("Qoder API Key (可选): ").strip()
    
    print("\n服务器配置：")
    server_port = input("服务端口 (默认: 5000): ").strip() or "5000"
    
    env_content = f"""# 飞书配置
FEISHU_APP_ID={app_id}
FEISHU_APP_SECRET={app_secret}
FEISHU_VERIFICATION_TOKEN={verification_token}
FEISHU_ENCRYPT_KEY={encrypt_key}

# Qoder配置
QODER_API_ENDPOINT={qoder_endpoint}
QODER_API_KEY={qoder_api_key}

# 服务配置
SERVER_HOST=0.0.0.0
SERVER_PORT={server_port}
DEBUG=False

# 日志配置
LOG_LEVEL=INFO
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("\n✅ .env文件创建成功")
    return True


def check_ngrok():
    """检查ngrok是否安装"""
    print("\n检查ngrok（内网穿透工具）...")
    try:
        result = subprocess.run(['ngrok', 'version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            print(f"✅ ngrok已安装: {result.stdout.strip()}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    print("❌ ngrok未安装")
    print("\n开发环境需要ngrok将本地服务暴露到公网")
    print("安装方法：")
    print("  macOS: brew install ngrok")
    print("  或访问: https://ngrok.com/download")
    
    return False


def start_services():
    """启动服务"""
    print_header("启动服务")
    
    print("1. 启动飞书机器人服务")
    print("2. 启动ngrok内网穿透（开发环境）")
    print("3. 两者都启动")
    print("0. 跳过")
    
    choice = input("\n请选择 (默认: 3): ").strip() or "3"
    
    if choice == "0":
        return
    
    if choice in ["1", "3"]:
        print("\n正在启动飞书机器人服务...")
        print("提示：服务将在新终端窗口中运行")
        
        # 根据操作系统选择终端命令
        if sys.platform == "darwin":  # macOS
            script = f'''
tell application "Terminal"
    do script "cd '{os.getcwd()}' && echo '启动飞书机器人服务...' && python feishu_bot.py"
    activate
end tell
'''
            subprocess.Popen(['osascript', '-e', script])
            print("✅ 飞书机器人服务已在新终端启动")
        else:
            print("请在新终端中手动执行: python feishu_bot.py")
    
    if choice in ["2", "3"]:
        has_ngrok = check_ngrok()
        if not has_ngrok:
            print("\n请先安装ngrok，然后在新终端中执行: ngrok http 5000")
            return
        
        # 获取端口
        from dotenv import load_dotenv
        load_dotenv()
        port = os.getenv("SERVER_PORT", "5000")
        
        print(f"\n正在启动ngrok (端口 {port})...")
        if sys.platform == "darwin":  # macOS
            script = f'''
tell application "Terminal"
    do script "cd '{os.getcwd()}' && echo '启动ngrok内网穿透...' && ngrok http {port}"
    activate
end tell
'''
            subprocess.Popen(['osascript', '-e', script])
            print("✅ ngrok已在新终端启动")
        else:
            print(f"请在新终端中手动执行: ngrok http {port}")
        
        print("\n⚠️  重要提示：")
        print("1. 查看ngrok终端，找到 'Forwarding' 行")
        print("2. 复制 https://xxxx.ngrok.io 地址")
        print("3. 在飞书开放平台配置回调地址: https://xxxx.ngrok.io/feishu/callback")


def show_callback_config_guide():
    """显示回调配置指南"""
    print_header("飞书开放平台回调配置指南")
    
    print("📋 配置步骤：\n")
    
    print("1. 访问飞书开放平台")
    print("   https://open.feishu.cn/app\n")
    
    print("2. 选择您的应用，进入「事件订阅」页面\n")
    
    print("3. 配置回调地址")
    print("   开发环境: https://your-ngrok-domain.ngrok.io/feishu/callback")
    print("   生产环境: https://your-domain.com/feishu/callback\n")
    
    print("4. 订阅事件")
    print("   - im.message.receive_v1 (接收消息)")
    print("   - 选择「接收所有消息」或「仅接收@机器人的消息」\n")
    
    print("5. 配置权限")
    print("   进入「权限管理」，开通以下权限：")
    print("   - im:message (获取与发送单聊、群组消息)")
    print("   - im:message.group_at_msg (接收群聊中@机器人消息)")
    print("   - im:message.p2p_msg (接收单聊消息)\n")
    
    print("6. 发布版本")
    print("   配置完成后，创建并发布应用版本\n")
    
    print("⚠️  注意事项：")
    print("- 回调地址必须是公网可访问的 HTTPS 地址")
    print("- 开发环境可以使用 ngrok 提供的临时域名")
    print("- 保存回调地址时，飞书会发送验证请求")
    print("- 确保服务已启动，否则验证会失败\n")


def test_service():
    """测试服务"""
    print_header("测试服务")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    port = os.getenv("SERVER_PORT", "5000")
    base_url = f"http://localhost:{port}"
    
    print(f"正在测试服务 {base_url} ...\n")
    
    try:
        import requests
        
        # 测试健康检查
        print("1. 测试健康检查接口...")
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ 健康检查通过: {response.json()}")
        else:
            print(f"   ❌ 健康检查失败: {response.status_code}")
            return False
        
        # 测试回调接口
        print("\n2. 测试回调接口（URL验证）...")
        test_data = {
            "type": "url_verification",
            "challenge": "test_challenge_123",
            "token": os.getenv("FEISHU_VERIFICATION_TOKEN", "test")
        }
        response = requests.post(f"{base_url}/feishu/callback", json=test_data, timeout=5)
        if response.status_code == 200 and response.json().get("challenge") == "test_challenge_123":
            print(f"   ✅ 回调接口正常: {response.json()}")
        else:
            print(f"   ❌ 回调接口异常: {response.status_code} {response.text}")
            return False
        
        print("\n✅ 所有测试通过！服务运行正常")
        return True
        
    except ImportError:
        print("❌ 缺少requests库，请先安装依赖")
        return False
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到服务 {base_url}")
        print("   请确保服务已启动: python feishu_bot.py")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def main():
    """主函数"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "飞书机器人配置助手" + " " * 15 + "║")
    print("║" + " " * 12 + "Qoder x 飞书 集成配置" + " " * 12 + "║")
    print("╚" + "=" * 58 + "╝")
    
    # 1. 检查环境
    print_header("步骤 1/5: 检查环境")
    if not check_python_version():
        return 1
    
    if not check_dependencies():
        print("\n⚠️  请先安装依赖包，然后重新运行此脚本")
        return 1
    
    # 2. 创建配置文件
    print_header("步骤 2/5: 创建配置文件")
    if not create_env_file():
        return 1
    
    # 3. 检查ngrok
    print_header("步骤 3/5: 检查开发工具")
    check_ngrok()
    
    # 4. 启动服务
    print_header("步骤 4/5: 启动服务")
    start_services()
    
    # 等待服务启动
    print("\n等待服务启动...")
    import time
    time.sleep(3)
    
    # 5. 测试服务
    print_header("步骤 5/5: 测试服务")
    test_service()
    
    # 显示配置指南
    show_callback_config_guide()
    
    print("\n" + "=" * 60)
    print("配置完成！")
    print("=" * 60)
    print("\n下一步操作：")
    print("1. 查看ngrok终端，复制公网地址（https://xxxx.ngrok.io）")
    print("2. 访问飞书开放平台配置回调地址")
    print("3. 在飞书中@机器人，测试对话功能")
    print("\n运行测试: python test_bot.py")
    print("查看日志: 检查运行飞书机器人的终端窗口\n")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n配置已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
