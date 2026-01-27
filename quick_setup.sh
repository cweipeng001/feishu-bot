#!/bin/bash

# 飞书机器人快速配置脚本

echo "=================================="
echo "  飞书机器人快速配置向导"
echo "=================================="

# 1. 安装依赖
echo ""
echo "步骤 1/4: 安装依赖包"
echo "----------------------------------"
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败"
    exit 1
fi
echo "✅ 依赖安装完成"

# 2. 创建.env文件
echo ""
echo "步骤 2/4: 配置环境变量"
echo "----------------------------------"

if [ -f ".env" ]; then
    echo "⚠️  .env文件已存在"
    read -p "是否覆盖？(y/n): " overwrite
    if [ "$overwrite" != "y" ]; then
        echo "跳过创建.env文件"
    else
        rm .env
    fi
fi

if [ ! -f ".env" ]; then
    echo ""
    echo "请输入飞书机器人配置（从飞书开放平台获取）："
    echo "官方地址: https://open.feishu.cn/app"
    echo ""
    
    read -p "App ID: " app_id
    read -p "App Secret: " app_secret
    read -p "Verification Token: " verification_token
    read -p "Encrypt Key (可选，直接回车跳过): " encrypt_key
    
    echo ""
    echo "Qoder配置："
    read -p "Qoder API端点 (默认: http://localhost:8080/api/chat): " qoder_endpoint
    qoder_endpoint=${qoder_endpoint:-http://localhost:8080/api/chat}
    read -p "Qoder API Key (可选): " qoder_api_key
    
    echo ""
    read -p "服务端口 (默认: 5000): " server_port
    server_port=${server_port:-5000}
    
    # 创建.env文件
    cat > .env << EOF
# 飞书配置
FEISHU_APP_ID=$app_id
FEISHU_APP_SECRET=$app_secret
FEISHU_VERIFICATION_TOKEN=$verification_token
FEISHU_ENCRYPT_KEY=$encrypt_key

# Qoder配置
QODER_API_ENDPOINT=$qoder_endpoint
QODER_API_KEY=$qoder_api_key

# 服务配置
SERVER_HOST=0.0.0.0
SERVER_PORT=$server_port
DEBUG=False

# 日志配置
LOG_LEVEL=INFO
EOF
    
    echo "✅ .env文件创建完成"
fi

# 3. 检查ngrok
echo ""
echo "步骤 3/4: 检查ngrok"
echo "----------------------------------"
if command -v ngrok &> /dev/null; then
    echo "✅ ngrok已安装"
else
    echo "❌ ngrok未安装"
    echo ""
    echo "开发环境需要ngrok将本地服务暴露到公网"
    echo "安装方法: brew install ngrok"
    echo "或访问: https://ngrok.com/download"
fi

# 4. 显示启动说明
echo ""
echo "步骤 4/4: 启动服务"
echo "----------------------------------"
echo ""
echo "请按照以下步骤操作："
echo ""
echo "1️⃣  在当前终端启动飞书机器人服务："
echo "   python3 feishu_bot.py"
echo ""
echo "2️⃣  在新终端启动ngrok（如果是开发环境）："
echo "   cd \"$PWD\""
echo "   ngrok http 5000"
echo ""
echo "3️⃣  配置飞书开放平台："
echo "   - 访问: https://open.feishu.cn/app"
echo "   - 进入你的应用 > 事件订阅"
echo "   - 回调地址填写: https://your-ngrok-domain.ngrok.io/feishu/callback"
echo "   - 订阅事件: im.message.receive_v1"
echo ""
echo "4️⃣  在飞书中测试："
echo "   - 添加机器人到群组"
echo "   - @机器人发送消息"
echo ""
echo "=================================="
echo "配置完成！"
echo "=================================="
