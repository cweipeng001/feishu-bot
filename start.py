#!/usr/bin/env python3
"""
飞书机器人一键启动脚本
"""

import subprocess
import sys
import os
import time
import webbrowser

def print_step(step_num, title):
    print(f"\n{'='*60}")
    print(f"  步骤 {step_num}: {title}")
    print(f"{'='*60}\n")

def check_env_file():
    """检查环境配置文件"""
    print_step(1, "检查配置文件")
    
    if not os.path.exists('.env'):
        print("❌ .env 文件不存在")
        print("请先运行: ./quick_setup.sh")
        return False
    
    # 读取配置
    with open('.env', 'r') as f:
        content = f.read()
    
    if '不知道' in content:
        print("⚠️  检测到 Verification Token 未正确配置")
        print("\n请执行以下命令获取并更新 Token:")
        print("  python3 get_token.py")
        print("\n或手动编辑 .env 文件")
        
        choice = input("\n是否现在更新 Token? (y/n): ").lower()
        if choice == 'y':
            subprocess.run(['python3', 'get_token.py'])
        else:
            return False
    
    print("✅ 配置文件检查通过")
    return True

def check_ngrok():
    """检查并安装 ngrok"""
    print_step(2, "检查 ngrok")
    
    try:
        result = subprocess.run(['ngrok', 'version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            print(f"✅ ngrok 已安装")
            return True
    except:
        pass
    
    # 检查当前目录是否有 ngrok
    if os.path.exists('./ngrok'):
        print("✅ ngrok 已存在于当前目录")
        return True
    
    print("❌ ngrok 未安装")
    choice = input("\n是否现在安装 ngrok? (y/n): ").lower()
    
    if choice == 'y':
        print("\n正在安装 ngrok...")
        subprocess.run(['bash', 'install_ngrok.sh'])
        return True
    else:
        print("\n⚠️  跳过 ngrok 安装")
        print("   如果您有公网服务器，可以不使用 ngrok")
        return True

def start_bot_service():
    """启动飞书机器人服务"""
    print_step(3, "启动飞书机器人服务")
    
    print("正在新终端窗口中启动服务...")
    
    # macOS 使用 osascript 打开新终端
    script = f'''
tell application "Terminal"
    do script "cd '{os.getcwd()}' && python3 feishu_bot.py"
    activate
end tell
'''
    
    try:
        subprocess.Popen(['osascript', '-e', script])
        print("✅ 服务已在新终端启动")
        time.sleep(2)
        return True
    except Exception as e:
        print(f"❌ 无法自动启动，请手动在新终端执行:")
        print(f"   cd {os.getcwd()}")
        print("   python3 feishu_bot.py")
        return False

def start_ngrok():
    """启动 ngrok"""
    print_step(4, "启动 ngrok 内网穿透")
    
    # 确定 ngrok 命令
    ngrok_cmd = 'ngrok'
    if os.path.exists('./ngrok'):
        ngrok_cmd = './ngrok'
    
    print("正在新终端窗口中启动 ngrok...")
    
    script = f'''
tell application "Terminal"
    do script "cd '{os.getcwd()}' && {ngrok_cmd} http 5000"
    activate
end tell
'''
    
    try:
        subprocess.Popen(['osascript', '-e', script])
        print("✅ ngrok 已在新终端启动")
        time.sleep(3)
        return True
    except Exception as e:
        print(f"❌ 无法自动启动，请手动在新终端执行:")
        print(f"   cd {os.getcwd()}")
        print(f"   {ngrok_cmd} http 5000")
        return False

def show_final_instructions():
    """显示最终配置说明"""
    print_step(5, "配置飞书回调地址")
    
    print("""
📋 请按照以下步骤完成配置：

1️⃣  查看 ngrok 终端窗口，找到类似这样的信息：
   ┌────────────────────────────────────────────────┐
   │ Forwarding   https://xxxx.ngrok.io -> http:// │
   └────────────────────────────────────────────────┘

2️⃣  复制 https://xxxx.ngrok.io 地址

3️⃣  打开飞书开放平台（即将自动打开浏览器）
   https://open.feishu.cn/app

4️⃣  进入您的应用 > 事件订阅

5️⃣  在"请求地址"中填入：
   https://xxxx.ngrok.io/feishu/callback
   （将 xxxx.ngrok.io 替换为您的 ngrok 地址）

6️⃣  点击保存，等待验证通过

7️⃣  订阅事件：im.message.receive_v1

8️⃣  在飞书中添加机器人到群组，@机器人发送消息测试
    """)
    
    input("\n按回车键打开飞书开放平台...")
    webbrowser.open('https://open.feishu.cn/app')
    
    print("\n" + "="*60)
    print("  🎉 启动完成！")
    print("="*60)
    print("\n提示：")
    print("- 查看飞书机器人服务日志：检查第一个终端窗口")
    print("- 查看 ngrok 状态：检查第二个终端窗口")
    print("- 运行测试：python3 test_bot.py")
    print("")

def main():
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "飞书机器人一键启动" + " "*15 + "║")
    print("╚" + "="*58 + "╝")
    
    # 检查环境
    if not check_env_file():
        print("\n❌ 配置检查失败，请先完成配置")
        return 1
    
    # 检查 ngrok
    if not check_ngrok():
        return 1
    
    # 启动服务
    if not start_bot_service():
        return 1
    
    # 启动 ngrok
    if not start_ngrok():
        return 1
    
    # 显示配置说明
    show_final_instructions()
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n已取消")
        sys.exit(1)
