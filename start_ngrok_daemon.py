#!/usr/bin/env python3
"""
ngrok 隧道守护进程
自动启动和监控 ngrok，保持飞书回调地址始终可用
"""

import subprocess
import time
import sys
import os
import requests
from pathlib import Path

def get_ngrok_url():
    """获取当前 ngrok 的公网 URL"""
    try:
        response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
        data = response.json()
        if data.get('tunnels'):
            for tunnel in data['tunnels']:
                if tunnel.get('proto') == 'https':
                    return tunnel.get('public_url')
        return None
    except:
        return None

def start_ngrok():
    """启动 ngrok 隧道"""
    print("\n" + "="*60)
    print("🌐 启动 ngrok 隧道守护进程...")
    print("="*60)
    
    try:
        # 启动 ngrok - 转发本地 5004 端口
        process = subprocess.Popen(
            ['ngrok', 'http', '5004'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"✓ ngrok 进程启动成功 (PID: {process.pid})")
        return process
    except FileNotFoundError:
        print("✗ 错误：找不到 ngrok 命令")
        print("  请先安装 ngrok：brew install ngrok")
        return None
    except Exception as e:
        print(f"✗ 启动失败: {e}")
        return None

def monitor_ngrok():
    """监控 ngrok 隧道，崩溃时自动重启"""
    print("\n📡 进入监控模式...\n")
    
    process = None
    restart_count = 0
    last_url = None
    
    while True:
        try:
            # 如果进程未运行，启动它
            if process is None or process.poll() is not None:
                if process and process.poll() is not None:
                    restart_count += 1
                    print(f"\n⚠️  ngrok 已停止 (退出码: {process.returncode})")
                    print(f"📊 重启次数: {restart_count}")
                    time.sleep(3)
                
                process = start_ngrok()
                if process is None:
                    print("✗ 启动失败，等待30秒后重试...")
                    time.sleep(30)
                    continue
            
            # 每5秒检查一次 ngrok 状态
            time.sleep(5)
            
            # 检查进程是否还活着
            if process and process.poll() is None:
                # 获取当前 URL
                url = get_ngrok_url()
                if url:
                    if url != last_url:
                        print(f"\n✓ ngrok 隧道已启动 (PID: {process.pid})")
                        print(f"🔗 公网地址: {url}")
                        print(f"📝 回调地址: {url}/feishu/callback")
                        print(f"\n⚠️  请立即在飞书应用中更新回调地址！")
                        last_url = url
                    else:
                        print(f"✓ ngrok 运行中 - {time.strftime('%H:%M:%S')}")
            
        except KeyboardInterrupt:
            print("\n\n🛑 收到停止信号...")
            if process:
                print(f"正在停止 ngrok (PID: {process.pid})...")
                process.terminate()
                time.sleep(2)
                if process.poll() is None:
                    process.kill()
            print("✓ ngrok 已停止")
            break
        except Exception as e:
            print(f"✗ 监控错误: {e}")
            time.sleep(5)

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════╗
║       ngrok 隧道守护进程 v1.0                          ║
║   自动启动和监控，保持飞书回调地址始终可用             ║
╚════════════════════════════════════════════════════════╝
    """)
    
    print(f"🔌 监控本地端口: 5004 (飞书机器人)")
    print(f"🌐 ngrok 管理后台: http://localhost:4040")
    print(f"📋 按 Ctrl+C 停止守护进程\n")
    
    monitor_ngrok()
