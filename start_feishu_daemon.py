#!/usr/bin/env python3
"""
飞书机器人服务守护进程
自动启动和监控 feishu_bot.py，确保其持续运行
"""

import subprocess
import time
import sys
import os
from pathlib import Path

# 获取当前脚本所在目录
SCRIPT_DIR = Path(__file__).parent
BOT_SCRIPT = SCRIPT_DIR / "feishu_bot.py"

def kill_process_on_port(port=5004):
    """杀死占用指定端口的进程"""
    try:
        os.system(f"lsof -ti:{port} | xargs kill -9 2>/dev/null")
        print(f"✓ 已清理端口 {port} 上的旧进程")
        time.sleep(1)
    except:
        pass

def start_feishu_bot():
    """启动飞书机器人"""
    print("\n" + "="*60)
    print("🤖 启动飞书机器人守护进程...")
    print("="*60)
    
    # 清理旧进程
    kill_process_on_port(5004)
    
    try:
        # 启动 feishu_bot.py
        process = subprocess.Popen(
            [sys.executable, str(BOT_SCRIPT)],
            cwd=SCRIPT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        print(f"✓ 飞书机器人进程启动成功 (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"✗ 启动失败: {e}")
        return None

def monitor_feishu_bot():
    """监控飞书机器人，崩溃时自动重启"""
    print("\n📡 进入监控模式...\n")
    
    process = None
    restart_count = 0
    
    while True:
        try:
            # 如果进程未运行，启动它
            if process is None or process.poll() is not None:
                if process and process.poll() is not None:
                    restart_count += 1
                    print(f"\n⚠️  飞书机器人已停止 (退出码: {process.returncode})")
                    print(f"📊 重启次数: {restart_count}")
                    time.sleep(2)  # 等待2秒后重启
                
                process = start_feishu_bot()
                if process is None:
                    print("✗ 启动失败，等待30秒后重试...")
                    time.sleep(30)
                    continue
            
            # 每10秒检查一次进程状态
            time.sleep(10)
            
            # 检查进程是否还活着
            if process and process.poll() is None:
                print(f"✓ 飞书机器人运行中 (PID: {process.pid}) - {time.strftime('%H:%M:%S')}")
            
        except KeyboardInterrupt:
            print("\n\n🛑 收到停止信号...")
            if process:
                print(f"正在停止飞书机器人 (PID: {process.pid})...")
                process.terminate()
                time.sleep(2)
                if process.poll() is None:
                    process.kill()
            print("✓ 飞书机器人已停止")
            break
        except Exception as e:
            print(f"✗ 监控错误: {e}")
            time.sleep(5)

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════╗
║     飞书机器人服务守护进程 v1.0                         ║
║     自动启动和监控，确保持续可用                       ║
╚════════════════════════════════════════════════════════╝
    """)
    
    if not BOT_SCRIPT.exists():
        print(f"✗ 错误：找不到 {BOT_SCRIPT}")
        print(f"  请确保当前目录是: {SCRIPT_DIR}")
        sys.exit(1)
    
    print(f"📂 服务脚本: {BOT_SCRIPT}")
    print(f"🔌 监控端口: 5004")
    print(f"📋 按 Ctrl+C 停止守护进程\n")
    
    monitor_feishu_bot()
