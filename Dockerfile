FROM python:3.9-slim

WORKDIR /app

# 安装 Node.js（飞书 MCP 客户端需要）
RUN apt-get update && apt-get install -y curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 验证 Node.js 安装
RUN node --version && npm --version

# 预先安装飞书 MCP 包（避免运行时下载超时）
RUN npm install -g @larksuiteoapi/lark-mcp && npm cache clean --force

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目文件
COPY . .

# 暴露端口
EXPOSE 5000

# 启动服务（同时运行飞书机器人 + Qoder）
CMD ["python", "start_all.py"]
