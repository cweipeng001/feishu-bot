#!/usr/bin/env python3
"""
统一启动脚本 - 同时启动飞书机器人和Qoder服务
用于云平台部署（Railway等）
"""

import subprocess
import sys
import os
import time
import signal

processes = []

def cleanup(signum, frame):
    """清理所有子进程"""
    print("\n🛑 收到停止信号，正在关闭服务...")
    for p in processes:
        try:
            p.terminate()
        except:
            pass
    sys.exit(0)

signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

def main():
    print("=" * 60)
    print("🚀 飞书机器人 + Qoder 服务启动中...")
    print("=" * 60)
    
    # 获取端口配置
    feishu_port = os.getenv("PORT", "5000")  # Railway 会设置 PORT 环境变量
    qoder_port = os.getenv("QODER_PORT", "8081")
    
    # 更新 Qoder 端点为内部地址
    os.environ["QODER_API_ENDPOINT"] = f"http://127.0.0.1:{qoder_port}/api/chat"
    
    print(f"📱 飞书机器人端口: {feishu_port}")
    print(f"🤖 Qoder服务端口: {qoder_port}")
    print(f"🔗 Qoder内部地址: http://127.0.0.1:{qoder_port}/api/chat")
    print("=" * 60)
    
    # 启动 Qoder 服务（后台）
    print("\n🤖 启动 Qoder 千问服务...")
    qoder_env = os.environ.copy()
    qoder_process = subprocess.Popen(
        [sys.executable, "qoder_qwen.py"],
        env=qoder_env
    )
    processes.append(qoder_process)
    print(f"✅ Qoder 服务启动成功 (PID: {qoder_process.pid})") 
    
    # 等待 Qoder 启动
    time.sleep(3)
    
    # 启动飞书机器人（前台，使用 gunicorn）
    print("\n📱 启动飞书机器人...")
    feishu_process = subprocess.Popen(
        ["gunicorn", "-w", "2", "-b", f"0.0.0.0:{feishu_port}", 
         "feishu_bot:app", "--timeout", "120", "--access-logfile", "-"],
        env=os.environ.copy()
    )
    processes.append(feishu_process)
    print(f"✅ 飞书机器人启动成功 (PID: {feishu_process.pid})")
    
    print("\n" + "=" * 60)
    print("🎉 所有服务已启动！")
    print("=" * 60)
    
    # 等待主进程
    try:
        feishu_process.wait()
    except KeyboardInterrupt:
        cleanup(None, None)

if __name__ == "__main__":
    main()
