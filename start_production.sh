#!/bin/bash

# 生产环境部署脚本
set -e

# 加载环境变量
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "🚀 开始部署飞书机器人生产环境..."

# 创建必要的目录
mkdir -p logs backup

# 备份当前配置
cp .env backup/.env.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

echo "📋 检查环境配置..."
if [ ! -f ".env" ]; then
    echo "❌ 错误: 找不到 .env 配置文件"
    exit 1
fi

echo "📦 安装依赖..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --upgrade
else
    echo "⚠️  requirements.txt 不存在，跳过依赖安装"
fi

echo "🔍 验证配置..."
# 检查必要环境变量
if [ -z "$(grep '^FEISHU_APP_ID=' .env | cut -d'=' -f2)" ] || [ -z "$(grep '^FEISHU_APP_SECRET=' .env | cut -d'=' -f2)" ]; then
    echo "❌ 错误: 缺少飞书 App 配置，请检查 .env 文件"
    exit 1
fi

echo "🧪 测试连接..."
# 简单测试 REST API 连接
python3 -c "
import os
os.environ.setdefault('BOT_RUNTIME_MODE', 'rest_api')
from feishu_auth import is_user_authorized
if not is_user_authorized():
    print('⚠️  用户未授权，但服务仍可启动')
else:
    print('✅ 用户已授权')
" || echo "⚠️  授权检查失败，但不影响启动"

echo "🚀 启动生产服务..."

# 使用 nohup 在后台运行
cat > run_bot.sh << 'EOF'
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
EOF

chmod +x run_bot.sh

# 启动服务
nohup ./run_bot.sh > logs/startup.log 2>&1 &
BOT_PID=$!

echo "✅ 服务已在后台启动 (PID: $BOT_PID)"
echo "📋 日志文件: logs/bot_$(date +%Y%m%d).log"
echo "📊 状态检查: curl http://localhost:5004/health"
echo "🛑 停止服务: kill $BOT_PID"

echo "⏳ 等待服务启动..."
sleep 3

echo "🔍 检查服务状态..."
if curl -s http://localhost:5004/health > /dev/null; then
    echo "🎉 部署成功！服务运行正常"
    echo "🔗 服务地址: http://localhost:5004"
else
    echo "⚠️  服务可能启动失败，请检查日志: tail -f logs/bot_$(date +%Y%m%d).log"
fi