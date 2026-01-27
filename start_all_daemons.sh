#!/bin/bash

# 启动所有守护进程脚本
# 用法: ./start_all_daemons.sh

cd "$(dirname "$0")"

echo "╔════════════════════════════════════════════════════════╗"
echo "║       飞书机器人完整守护系统 v1.0                      ║"
echo "║   启动 Qoder 千问服务 + 飞书机器人双守护               ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# 确保脚本存在
if [ ! -f "start_qoder_daemon.py" ]; then
    echo "✗ 错误：找不到 start_qoder_daemon.py"
    exit 1
fi

if [ ! -f "start_feishu_daemon.py" ]; then
    echo "✗ 错误：找不到 start_feishu_daemon.py"
    exit 1
fi

echo "🚀 在后台启动 Qoder 千问服务守护进程..."
python3 start_qoder_daemon.py > /tmp/qoder_daemon.log 2>&1 &
QODER_PID=$!
echo "✓ Qoder 守护进程启动 (PID: $QODER_PID)"

# 等待 Qoder 启动
sleep 3

echo ""
echo "🚀 在后台启动飞书机器人守护进程..."
python3 start_feishu_daemon.py > /tmp/feishu_daemon.log 2>&1 &
FEISHU_PID=$!
echo "✓ 飞书机器人守护进程启动 (PID: $FEISHU_PID)"

echo ""
echo "════════════════════════════════════════════════════════"
echo "✅ 所有守护进程已启动！"
echo "════════════════════════════════════════════════════════"
echo ""
echo "📊 运行状态:"
echo "  🔌 Qoder 千问服务 (端口 8081): http://localhost:8081/health"
echo "  📱 飞书机器人 (端口 5004): http://localhost:5004/health"
echo ""
echo "📋 日志位置:"
echo "  Qoder 日志: /tmp/qoder_daemon.log"
echo "  飞书机器人日志: /tmp/feishu_daemon.log"
echo ""
echo "🛑 停止方式:"
echo "  kill $QODER_PID      # 停止 Qoder 服务"
echo "  kill $FEISHU_PID     # 停止飞书机器人"
echo ""
echo "💾 进程保存:"
echo "  Qoder PID: $QODER_PID"
echo "  Feishu PID: $FEISHU_PID"
echo ""

# 保持脚本运行，显示监控信息
while true; do
    echo "✓ 所有服务运行中 - $(date '+%Y-%m-%d %H:%M:%S')"
    sleep 30
done
