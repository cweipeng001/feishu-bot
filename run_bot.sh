#!/bin/bash
cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 传递环境变量到 Python 进程
export SERVER_PORT=${SERVER_PORT:-5004}

while true; do
    echo "[$(date)] 启动飞书机器人服务..."
    python3 feishu_bot.py 2>&1 | tee -a logs/bot_$(date +%Y%m%d).log
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo "[$(date)] 服务正常退出"
        break
    else
        echo "[$(date)] 服务异常退出，5秒后重启..."
        sleep 5
    fi
done
