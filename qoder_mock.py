#!/usr/bin/env python3
"""
Qoder Mock服务 - 模拟Qoder AI智能体API
用于测试飞书机器人与AI的集成
"""

from flask import Flask, request, jsonify
import json
import logging

app = Flask(__name__)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 模拟AI回复（支持对话历史）
def get_ai_response(message, history=None):
    """根据消息内容和对话历史返回AI风格的回复"""
    message_lower = message.lower()
    
    # 如果有对话历史，先尝试上下文理解
    if history and len(history) > 0:
        # 获取最近的对话
        last_messages = history[-3:]  # 最近3轮对话
        context_text = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in last_messages])
        
        logger.info(f"对话上下文:\n{context_text}")
        
        # 处理后续问题（基于上下文）
        if any(word in message_lower for word in ['为什么', 'why', '怎么', 'how', '呢']):
            # 查找上一条assistant的回复
            for msg in reversed(last_messages):
                if msg.get('role') == 'assistant':
                    prev_reply = msg.get('content', '')
                    return f"我刚才提到“{prev_reply[:30]}...”。具体来说，这是因为目前的技术限制。作为AI助手，我的能力主要集中在文本对话和信息提供上。对于实时数据（如天气、新闻等），需要调用专门的API接口。"
            
        # 处理"什么xxx"类型的问题
        if message_lower.startswith(('什么', '哪些', 'what', 'which')) or '说了什么' in message_lower or '前面' in message_lower:
            # 查找上一条user的消息
            user_messages = [msg for msg in last_messages if msg.get('role') == 'user']
            if len(user_messages) > 1:
                # 获取倒数第二条用户消息（当前这条是最后一条）
                prev_user_msg = user_messages[-2].get('content', '')
                return f"根据我的记录，您之前说的是：\"{prev_user_msg}\"。\n\n这是我们对话的上下文。您想继续讨论这个话题吗？"
                    
            # 查找上一条assistant提到的关键词
            for msg in reversed(last_messages):
                if msg.get('role') == 'assistant':
                    prev_reply = msg.get('content', '')
                    # 提取关键词
                    if '知识点' in prev_reply:
                        return "我提到的知识点包括：\n\n1. **AI能力边界** - AI助手可以处理文本对话，但无法直接获取实时数据\n2. **数据源** - 实时信息需要通过API调用第三方服务\n3. **用户体验** - 建议用户使用专业工具获取准确信息\n\n希望这些解释对您有帮助！"
                    elif '分析' in prev_reply or '角度' in prev_reply:
                        return "我刚才提到可以从几个角度分析，具体包括：技术实现、用户需求、产品设计等方面。您对哪个角度比较感兴趣呢？"
                    break
        
        # 处理简短的后续问题
        if len(message) <= 5 and any(word in message_lower for word in ['哦', '好', '对', '是', '然后']):
            return "明白了！您还有其他问题吗？我很乐意继续为您解答。"
    
    # 基本关键词匹配（原有逻辑）
    if any(word in message_lower for word in ['你好', 'hello', 'hi', '您好']):
        return "您好！我是Qoder AI助手，很高兴为您服务。我可以帮助您解答问题、提供信息和协助处理各种任务。有什么我可以帮您的吗？"
    
    elif any(word in message_lower for word in ['天气', 'temperature', 'weather']):
        return "我目前无法获取实时天气信息，但建议您可以查看天气预报应用获取准确的天气数据。"
    
    elif any(word in message_lower for word in ['帮助', 'help', '功能', '能力']):
        return "我是一个AI助手，可以帮您：\n\n• 回答各类问题\n• 提供信息查询\n• 进行智能对话\n• 协助解决问题\n\n请随时告诉我您的需求！"
    
    elif any(word in message_lower for word in ['谢谢', '感谢', 'thank']):
        return "不客气！很高兴能帮到您。如果您还有其他问题，随时告诉我哦！"
    
    elif any(word in message_lower for word in ['再见', '拜拜', 'bye']):
        return "再见！希望我们的对话对您有帮助。期待下次为您服务！"
    
    else:
        # 通用AI风格回复
        responses = [
            f"我理解您说的是：‘{message}’。这是一个很有趣的问题，让我思考一下...",
            f"关于‘{message}’，我的看法是...",
            f"您提到‘{message}’，这让我想到了一些相关的知识点...",
            f"对于‘{message}’这个问题，我认为可以从几个角度来分析...",
            f"感谢您分享‘{message}’，我很乐意就此与您深入探讨。"
        ]
        
        import random
        return responses[hash(message) % len(responses)]

@app.route('/api/chat', methods=['POST'])
def chat_api():
    """Qoder AI聊天API接口"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        user_id = data.get('user_id', 'unknown')
        chat_id = data.get('chat_id', 'unknown')
        history = data.get('history', [])  # 获取对话历史
        
        logger.info(f"收到Qoder请求 - 用户: {user_id}, 消息: {message}, 历史条数: {len(history)}")
        
        # 生成AI回复（携带历史上下文）
        reply = get_ai_response(message, history)
        
        response = {
            "reply": reply,
            "status": "success",
            "context": {
                "user_id": user_id,
                "chat_id": chat_id
            }
        }
        
        logger.info(f"返回Qoder回复: {reply[:50]}...")
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Qoder API错误: {e}")
        return jsonify({
            "reply": "抱歉，AI助手暂时无法处理您的请求，请稍后再试。",
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({"status": "healthy", "service": "qoder-mock-api"})

if __name__ == '__main__':
    print("=" * 50)
    print("Qoder Mock服务启动中...")
    print("API地址: http://localhost:8081/api/chat")
    print("=" * 50)
    app.run(host='0.0.0.0', port=8081, debug=False)