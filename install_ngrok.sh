#!/bin/bash

echo "========================================"
echo "  ngrok 安装脚本"
echo "========================================"

# 检测系统架构
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    NGROK_URL="https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-darwin-arm64.zip"
    echo "检测到 Apple Silicon (M1/M2/M3) 架构"
elif [ "$ARCH" = "x86_64" ]; then
    NGROK_URL="https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-darwin-amd64.zip"
    echo "检测到 Intel 架构"
else
    echo "❌ 不支持的架构: $ARCH"
    exit 1
fi

echo ""
echo "正在下载 ngrok..."
curl -Lo ngrok.zip "$NGROK_URL"

if [ $? -ne 0 ]; then
    echo "❌ 下载失败"
    exit 1
fi

echo "正在解压..."
unzip -o ngrok.zip

if [ $? -ne 0 ]; then
    echo "❌ 解压失败"
    rm ngrok.zip
    exit 1
fi

# 移动到 /usr/local/bin
echo "正在安装到系统..."
chmod +x ngrok
sudo mv ngrok /usr/local/bin/

if [ $? -ne 0 ]; then
    echo "⚠️  无法安装到 /usr/local/bin，尝试当前目录"
    chmod +x ngrok
    echo "ngrok 已保存在当前目录"
    echo "使用方法: ./ngrok http 5000"
else
    echo "✅ ngrok 安装成功！"
    echo "使用方法: ngrok http 5000"
fi

# 清理
rm -f ngrok.zip

echo ""
echo "验证安装..."
if command -v ngrok &> /dev/null; then
    ngrok version
else
    ./ngrok version 2>/dev/null || echo "请使用 ./ngrok 运行"
fi

echo ""
echo "========================================"
echo "安装完成！"
echo "========================================"
