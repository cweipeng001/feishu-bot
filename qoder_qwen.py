#!/usr/bin/env python3
"""
Qoder 通义千问服务 - 使用阿里云千问模型作为AI后端
连接心流平台 (api.xinliudada.com)
"""

from flask import Flask, request, jsonify
import requests
import json
import logging
import os
import time
from dotenv import load_dotenv
import urllib3

# 禁用SSL警告（用于测试心流平台）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

app = Flask(__name__)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 千问API配置
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_MODEL = os.getenv("QWEN_MODEL", "tstars2.0")  # 默认模型，可在.env中修改
# 心流平台的千问API端点（注意是 apis 不是 api）
QWEN_API_URL = "https://apis.iflow.cn/v1/chat/completions"

def call_qwen_api(message, history=None, retry_count=0):
    """调用千问API（支持重试）"""
    try:
        # 构建消息列表
        messages = []
        
        # 添加历史对话
        if history and len(history) > 0:
            for msg in history[-5:]:  # 最近5轮对话
                role = "user" if msg.get("role") == "user" else "assistant"
                messages.append({
                    "role": role,
                    "content": msg.get("content", "")
                })
        
        # 添加当前消息
        messages.append({
            "role": "user",
            "content": message
        })
        
        # 构建请求
        payload = {
            "model": QWEN_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "top_p": 0.95,
            "max_tokens": 2048  # 增加至 2048，支持更长的回复
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {QWEN_API_KEY}"
        }
        
        logger.info(f"调用千问API - 模型: {QWEN_MODEL}, 消息数: {len(messages)}, 重试: {retry_count}")
        
        # 发送请求（禁用SSL验证）
        # 超时时间改为 60 秒，心流平台千问 API 响应较慢
        response = requests.post(
            QWEN_API_URL, 
            json=payload, 
            headers=headers, 
            timeout=60,
            verify=False
        )
        response.raise_for_status()
        
        # 解析响应
        result = response.json()
        logger.info(f"千问API响应: {json.dumps(result, ensure_ascii=False)[:200]}")
        
        # 检查是否有choices字段
        if "choices" not in result or len(result["choices"]) == 0:
            error_msg = result.get("error", {}).get("message", "未知错误")
            logger.error(f"千问API错误: {error_msg}")
            return f"抱歉，AI服务返回错误: {error_msg}"
        
        choice = result["choices"][0]
        if "message" in choice:
            text = choice["message"].get("content", "")
            if text:
                return text
        
        logger.warning(f"千问返回格式异常: {result}")
        return "抱歉，我暂时无法回答这个问题。"
        
    except requests.exceptions.ConnectionError as e:
        logger.error(f"千问API连接错误 ({retry_count}/3): {str(e)[:100]}")
        if retry_count < 3:
            time.sleep(2)  # 等待后重试
            return call_qwen_api(message, history, retry_count + 1)
        return "抱歉，无法连接到AI服务。请稍后重试。"
    except requests.exceptions.RequestException as e:
        logger.error(f"千问API请求失败: {e}")
        return f"抱歉，AI服务暂时不可用。"
    except Exception as e:
        logger.error(f"千问API错误: {e}")
        return "抱歉，处理您的请求时出现了错误。"

@app.route('/api/chat', methods=['POST'])
def chat_api():
    """千问AI聊天API接口"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        user_id = data.get('user_id', 'unknown')
        chat_id = data.get('chat_id', 'unknown')
        history = data.get('history', [])
        
        logger.info(f"收到请求 - 用户: {user_id}, 消息: {message}, 历史条数: {len(history)}")
        
        # 检查API Key
        if not QWEN_API_KEY:
            logger.error("未配置QWEN_API_KEY")
            return jsonify({
                "reply": "❌ 错误：未配置千问API Key。请在.env文件中设置QWEN_API_KEY",
                "status": "error"
            }), 500
        
        # 调用千问API
        reply = call_qwen_api(message, history)
        
        response = {
            "reply": reply,
            "status": "success",
            "context": {
                "user_id": user_id,
                "chat_id": chat_id,
                "model": QWEN_MODEL,
                "platform": "Qwen"
            }
        }
        
        logger.info(f"✅ 千问回复: {reply[:100]}...")
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"API错误: {e}")
        return jsonify({
            "reply": "抱歉，AI助手暂时无法处理您的请求。",
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    api_key_status = "✅ 已配置" if QWEN_API_KEY else "❌ 未配置"
    return jsonify({
        "status": "healthy",
        "service": "qoder-qwen-api",
        "model": QWEN_MODEL,
        "platform": "阿里云千问",
        "api_endpoint": QWEN_API_URL,
        "api_key": api_key_status
    })

if __name__ == '__main__':
    print("=" * 70)
    print("🤖 Qoder 千问服务启动中...")
    print(f"📡 API地址: http://localhost:8081/api/chat")
    print(f"🧠 模型: {QWEN_MODEL}")
    print(f"🏢 平台: 心流平台")
    print(f"🔗 远程API: {QWEN_API_URL}")
    print(f"🔑 API Key: {'已配置 ✅' if QWEN_API_KEY else '未配置 ❌'}")
    print("=" * 70)
    
    if not QWEN_API_KEY:
        print("\n⚠️  警告：未检测到QWEN_API_KEY")
        print("请在 .env 文件中添加：")
        print("QWEN_API_KEY=sk-your-key-here\n")
    
    app.run(host='0.0.0.0', port=8081, debug=False)
