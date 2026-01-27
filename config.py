import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 飞书机器人配置
FEISHU_CONFIG = {
    "app_id": os.getenv("FEISHU_APP_ID", "你的飞书App ID"),
    "app_secret": os.getenv("FEISHU_APP_SECRET", "你的飞书App Secret"),
    "verification_token": os.getenv("FEISHU_VERIFICATION_TOKEN", "你的飞书Verification Token"),
    "encrypt_key": os.getenv("FEISHU_ENCRYPT_KEY", "")  # 如果开启了加密，填入加密密钥
}

# Qoder智能体配置
QODER_CONFIG = {
    "api_endpoint": os.getenv("QODER_API_ENDPOINT", "http://localhost:8080/api/chat"),
    "api_key": os.getenv("QODER_API_KEY", "你的Qoder API Key")
}

# 服务器配置
SERVER_CONFIG = {
    "host": os.getenv("SERVER_HOST", "0.0.0.0"),
    "port": int(os.getenv("SERVER_PORT", "5000")),
    "debug": os.getenv("DEBUG", "False").lower() == "true"
}

# 日志配置
LOG_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
}
