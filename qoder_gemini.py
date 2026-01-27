#!/usr/bin/env python3
"""
Qoder Gemini服务 - 使用Google Gemini作为AI后端
"""

from flask import Flask, request, jsonify
import requests
import json
import logging
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gemini API配置
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro")
# Gemini API使用v1beta版本
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_API_URL = f"{GEMINI_API_BASE}/models/{GEMINI_MODEL}:generateContent"

def call_gemini_api(message, history=None):
    """调用Gemini API"""
    try:
        # 构建对话内容
        contents = []
        
        # 添加历史对话
        if history and len(history) > 0:
            for msg in history[-5:]:  # 最近5轮对话
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.get("content", "")}]
                })
        
        # 添加当前消息
        contents.append({
            "role": "user",
            "parts": [{"text": message}]
        })
        
        # 构建请求
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            }
        }
        
        # 发送请求
        url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        # 解析响应
        result = response.json()
        logger.info(f"Gemini API原始响应: {json.dumps(result, ensure_ascii=False)[:300]}")
        
        # 检查是否有candidates字段
        if "candidates" not in result or len(result["candidates"]) == 0:
            error_msg = result.get("error", {}).get("message", "未知错误")
            logger.error(f"Gemini API错误: {error_msg}")
            return f"抱歉，AI服务返回错误: {error_msg}"
        
        candidate = result["candidates"][0]
        if "content" in candidate and "parts" in candidate["content"]:
            text = candidate["content"]["parts"][0].get("text", "")
            return text
        
        logger.warning(f"Gemini返回格式异常: {result}")
        return "抱歉，我暂时无法回答这个问题。"
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Gemini API请求失败: {e}")
        return f"抱歉，AI服务暂时不可用。错误信息: {str(e)}"
    except Exception as e:
        logger.error(f"Gemini API错误: {e}")
        return "抱歉，处理您的请求时出现了错误。"

@app.route('/api/chat', methods=['POST'])
def chat_api():
    """Gemini AI聊天API接口"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        user_id = data.get('user_id', 'unknown')
        chat_id = data.get('chat_id', 'unknown')
        history = data.get('history', [])
        
        logger.info(f"收到请求 - 用户: {user_id}, 消息: {message}, 历史条数: {len(history)}")
        
        # 检查API Key
        if not GEMINI_API_KEY:
            logger.error("未配置GEMINI_API_KEY")
            return jsonify({
                "reply": "❌ 错误：未配置Gemini API Key。请在.env文件中设置GEMINI_API_KEY",
                "status": "error"
            }), 500
        
        # 调用Gemini API
        reply = call_gemini_api(message, history)
        
        response = {
            "reply": reply,
            "status": "success",
            "context": {
                "user_id": user_id,
                "chat_id": chat_id,
                "model": GEMINI_MODEL
            }
        }
        
        logger.info(f"✅ Gemini回复: {reply[:100]}...")
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
    api_key_status = "✅ 已配置" if GEMINI_API_KEY else "❌ 未配置"
    return jsonify({
        "status": "healthy",
        "service": "qoder-gemini-api",
        "model": GEMINI_MODEL,
        "api_key": api_key_status
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🤖 Qoder Gemini服务启动中...")
    print(f"📡 API地址: http://localhost:8081/api/chat")
    print(f"🧠 模型: {GEMINI_MODEL}")
    print(f"🔑 API Key: {'已配置 ✅' if GEMINI_API_KEY else '未配置 ❌'}")
    print("=" * 60)
    
    if not GEMINI_API_KEY:
        print("\n⚠️  警告：未检测到GEMINI_API_KEY")
        print("请在 .env 文件中添加：")
        print("GEMINI_API_KEY=your-api-key-here\n")
    
    app.run(host='0.0.0.0', port=8081, debug=False)
