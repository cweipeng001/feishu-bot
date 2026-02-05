#!/bin/bash
# 飞书机器人守护脚本 - 确保服务永远运行

cd "$(dirname "$0")"

while true; do
    # 检查服务是否运行
    if ! pgrep -f "python3 feishu_bot.py" > /dev/null; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  服务已停止，正在重启..."
        nohup python3 feishu_bot.py > feishu_bot.log 2>&1 &
        sleep 3
    fi
    
    # 检查 Qoder 服务
    if ! pgrep -f "python3 qoder_qwen.py" > /dev/null; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  Qoder 服务已停止，正在重启..."
        nohup python3 qoder_qwen.py > qoder_qwen.log 2>&1 &
        sleep 3
    fi
    
    # 每 30 秒检查一次
    sleep 30
done
