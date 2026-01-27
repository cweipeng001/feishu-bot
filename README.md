# 飞书机器人与Qoder集成项目

这是一个将飞书机器人与Qoder智能体打通的集成项目，用户在飞书中与机器人会话，机器人会调用Qoder智能体来生成回复。

## 项目结构

```
飞书机器人项目/
├── feishu_bot.py          # 主服务文件
├── config.py              # 配置文件
├── requirements.txt       # Python依赖
├── .env.example           # 环境变量示例
└── README.md              # 本文件
```

## 功能特点

1. **飞书消息接收**：监听飞书机器人接收到的用户消息
2. **Qoder智能体调用**：将用户消息发送给Qoder智能体处理
3. **智能回复**：将Qoder的回复发送回飞书
4. **签名验证**：验证飞书回调请求的合法性
5. **Token缓存**：优化飞书访问令牌的获取
6. **日志记录**：完整的日志记录便于调试

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置飞书机器人

在飞书开放平台（https://open.feishu.cn/）创建应用：

1. 创建企业自建应用
2. 获取 `App ID` 和 `App Secret`
3. 获取 `Verification Token`
4. 配置机器人能力，添加权限：
   - `im:message` - 获取与发送单聊、群组消息
   - `im:message.group_at_msg` - 接收群聊中@机器人消息
   - `im:message.p2p_msg` - 接收单聊消息
5. 配置事件订阅，订阅以下事件：
   - `im.message.receive_v1` - 接收消息

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填入配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```
# 飞书配置
FEISHU_APP_ID=cli_xxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxx
FEISHU_VERIFICATION_TOKEN=xxxxxxxxxxxxx
FEISHU_ENCRYPT_KEY=

# Qoder配置
QODER_API_ENDPOINT=http://localhost:8080/api/chat
QODER_API_KEY=your_qoder_api_key

# 服务配置
SERVER_PORT=5000
```

### 4. 启动服务

```bash
python feishu_bot.py
```

服务将在 `http://0.0.0.0:5000` 启动。

### 5. 配置飞书回调地址

在飞书开放平台配置回调地址：

```
https://your-domain.com/feishu/callback
```

**注意**：
- 需要使用公网可访问的域名（可使用内网穿透工具如 ngrok）
- 必须使用 HTTPS（开发环境可以使用 HTTP）

## API接口

### 1. 飞书事件回调

- **路径**: `/feishu/callback`
- **方法**: POST
- **说明**: 接收飞书事件推送

### 2. 健康检查

- **路径**: `/health`
- **方法**: GET
- **说明**: 检查服务健康状态

### 3. 测试发送消息

- **路径**: `/test/send`
- **方法**: POST
- **请求体**:
```json
{
  "chat_id": "oc_xxxxxxxxxxxxx",
  "message": "测试消息"
}
```

## 工作流程

```
用户在飞书发送消息
    ↓
飞书服务器推送消息事件
    ↓
feishu_bot.py 接收事件 (/feishu/callback)
    ↓
验证签名和Token
    ↓
提取用户消息内容
    ↓
调用Qoder智能体API
    ↓
获取智能体回复
    ↓
发送回复到飞书
    ↓
用户在飞书收到回复
```

## Qoder集成说明

### Qoder API接口要求

Qoder智能体需要提供HTTP API接口，示例：

**请求**:
```json
POST /api/chat
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY

{
  "message": "用户的问题",
  "user_id": "user_123",
  "chat_id": "chat_456",
  "context": {
    "platform": "feishu",
    "source": "feishu_bot"
  }
}
```

**响应**:
```json
{
  "reply": "智能体的回复内容",
  "status": "success"
}
```

### 自定义Qoder集成

如果您的Qoder API格式不同，请修改 `feishu_bot.py` 中的 `get_qoder_reply()` 函数。

## 部署建议

### 开发环境

使用 ngrok 进行内网穿透：

```bash
ngrok http 5000
```

### 生产环境

1. **使用进程管理工具**（如 Supervisor、PM2）
2. **配置反向代理**（Nginx）
3. **启用HTTPS**
4. **配置日志轮转**
5. **监控服务健康状态**

### Docker部署

```bash
# 构建镜像
docker build -t feishu-qoder-bot .

# 运行容器
docker run -d -p 5000:5000 --env-file .env feishu-qoder-bot
```

## 故障排查

### 1. 收不到飞书消息

- 检查飞书开放平台事件订阅配置是否正确
- 检查回调地址是否可访问
- 查看飞书开放平台的推送日志
- 检查机器人权限配置

### 2. 无法发送消息到飞书

- 检查 App ID 和 App Secret 是否正确
- 检查机器人是否在群组中
- 检查 chat_id 是否正确
- 查看服务日志中的错误信息

### 3. Qoder智能体无响应

- 检查 Qoder API地址是否可访问
- 检查 API Key 是否正确
- 查看 Qoder 服务日志
- 检查网络连接

## 日志

服务日志包含以下信息：
- 飞书消息接收
- Qoder API调用
- 消息发送状态
- 错误和异常

## 安全建议

1. ✅ 验证飞书回调签名
2. ✅ 使用环境变量存储敏感信息
3. ✅ 不在代码中硬编码密钥
4. ✅ 使用HTTPS传输数据
5. ✅ 限制API访问频率
6. ✅ 记录操作日志

## 许可证

MIT License

## 联系方式

如有问题，请联系项目维护者。
