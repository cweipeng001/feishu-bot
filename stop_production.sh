#!/bin/bash

# 停止生产服务脚本

echo "🛑 停止飞书机器人服务..."

# 查找并停止服务进程
PIDS=$(ps aux | grep '[f]eishu_bot.py' | awk '{print $2}')

if [ -n "$PIDS" ]; then
    echo "找到运行中的服务进程: $PIDS"
    kill $PIDS 2>/dev/null
    sleep 2
    
    # 强制杀死残留进程
    kill -9 $PIDS 2>/dev/null
    
    echo "✅ 服务已停止"
else
    echo "ℹ️  没有找到运行中的服务进程"
fi

# 清理临时文件
rm -f run_bot.sh 2>/dev/null

echo "🧹 清理完成"