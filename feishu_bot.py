import requests
import json
import hashlib
import hmac
import base64
from flask import Flask, request, jsonify
import logging
import os
import time
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime
from threading import Thread  # 用于异步处理

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 飞书机器人核心配置（从环境变量读取）
FEISHU_CONFIG = {
    "app_id": os.getenv("FEISHU_APP_ID"),
    "app_secret": os.getenv("FEISHU_APP_SECRET"),
    "verification_token": os.getenv("FEISHU_VERIFICATION_TOKEN"),
    "encrypt_key": os.getenv("FEISHU_ENCRYPT_KEY", "")
}

# Qoder智能体配置（从环境变量读取）
QODER_CONFIG = {
    "api_endpoint": os.getenv("QODER_API_ENDPOINT", "http://127.0.0.1:8081/api/chat"),  # 默认本地Qoder
    "api_key": os.getenv("QODER_API_KEY", "")
}

# 千问AI配置（作为备用，当Qoder不可用时使用）
QWEN_CONFIG = {
    "api_key": os.getenv("QWEN_API_KEY", ""),
    "model": os.getenv("QWEN_MODEL", "qwen3-vl-plus"),
    "api_url": "https://apis.iflow.cn/v1/chat/completions"
}

# 对话历史记录（简单的内存存储）
conversation_history = defaultdict(list)
MAX_HISTORY_LENGTH = 10  # 每个用户保留最后10条对话

# 事件去重机制（防止飞书发送的重复事件）
processed_events = set()
processed_messages = set()  # 按照message_id去重，确保同一条消息只处理一次
MAX_PROCESSED_EVENTS = 1000  # 最多记录1000个事件ID

# 用户白名单（空则允许所有用户）
ALLOWED_USERS = set(os.getenv("ALLOWED_USERS", "").split(",")) if os.getenv("ALLOWED_USERS") else None

# 辅助函数：检查事件是否已经处理过（防止重复事件）
def is_event_processed(event_id):
    """检查事件是否已经处理"""
    return event_id in processed_events

def mark_event_processed(event_id):
    """标记事件为已处理"""
    processed_events.add(event_id)
    # 控制内存大小不超过上限
    if len(processed_events) > MAX_PROCESSED_EVENTS:
        pass

# 辅助函数：检查用户权限
def check_user_permission(user_id):
    """检查用户是否有权限使用机器人"""
    if ALLOWED_USERS is None:
        return True  # 没有配置白名单，允许所有用户
    return user_id in ALLOWED_USERS

# 辅助函数：添加对话历史
def add_to_history(user_id, message, role="user"):
    """添加消息到对话历史"""
    if user_id:
        conversation_history[user_id].append({
            "role": role,
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        # 保持历史记录在限制范围内
        if len(conversation_history[user_id]) > MAX_HISTORY_LENGTH:
            conversation_history[user_id] = conversation_history[user_id][-MAX_HISTORY_LENGTH:]

# 辅助函数：获取对话历史
def get_conversation_history(user_id, limit=5):
    """获取用户的对话历史"""
    if user_id and user_id in conversation_history:
        return conversation_history[user_id][-limit:]
    return []

# 辅助函数：格式化对话历史用于Qoder API
def format_history_for_qoder(history):
    """将对话历史格式化为Qoder API期望的格式"""
    formatted = []
    for msg in history:
        formatted.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })
    return formatted

# 异步处理消息（关键修复：防止飞书重试）
def process_message_async(chat_id, sender_id, user_text, message_id=None):
    """在后台线程中处理消息"""
    try:
        # ✅ 调试日志：打印message_id
        logger.info(f"🔑 收到message_id: {message_id}")
        
        # ✅ 方案3：从飞书API获取群聊历史（不使用内存）
        history = get_feishu_chat_history(chat_id, limit=20)
        logger.info(f"📊 从飞书获取到 {len(history)} 条对话历史（chat_id={chat_id}）")
        
        # ✅ 飞书API返回的格式已经是标准格式，直接使用
        formatted_history = history  # {"role": "user/assistant", "content": "..."}
        if formatted_history:
            logger.info(f"✅ 格式化历史：{len(formatted_history)} 条 -> {formatted_history[-2:]}")  # 打印最后2条
        
        # 调用Qoder智能体获取回复
        logger.info(f"用户消息：{user_text}")
        qoder_reply = get_qoder_reply(user_text, sender_id, chat_id, formatted_history)
        logger.info(f"Qoder回复：{qoder_reply}")
        
        # ✅ 关键修复：使用回复功能，而非普通发送
        logger.info(f"📤 准备发送回复，reply_to_message_id={message_id}")
        send_feishu_text_message(chat_id, qoder_reply, reply_to_message_id=message_id)
    except Exception as e:
        logger.error(f"异步处理消息失败：{e}", exc_info=True)

# 1. 获取飞书机器人访问令牌（带缓存）
_feishu_token_cache = {"token": None, "expire_time": 0}

def get_feishu_token():
    """获取飞书访问令牌，包含缓存机制"""
    # 检查缓存是否有效
    if _feishu_token_cache["token"] and _feishu_token_cache["expire_time"] > time.time():
        return _feishu_token_cache["token"]
    
    url = "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal"
    data = {
        "app_id": FEISHU_CONFIG["app_id"],
        "app_secret": FEISHU_CONFIG["app_secret"]
    }
    try:
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        token_data = response.json()
        
        if token_data.get("code") == 0:
            # 缓存token（提前5分钟过期）
            _feishu_token_cache["token"] = token_data["app_access_token"]
            _feishu_token_cache["expire_time"] = time.time() + token_data.get("expire", 7200) - 300
            logger.info("成功获取飞书Token")
            return token_data["app_access_token"]
        else:
            logger.error(f"获取飞书Token失败：{token_data}")
            return None
    except Exception as e:
        logger.error(f"获取飞书Token异常：{e}")
        return None

# 2. 发送飞书文本消息（支持回复功能）
def send_feishu_text_message(chat_id, text_content, msg_type="text", reply_to_message_id=None):
    """发送飞书消息（文本/富文本/卡片），支持回复功能"""
    token = get_feishu_token()
    if not token:
        return False
    
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 构造消息内容
    if msg_type == "text":
        content = json.dumps({"text": text_content})
    elif msg_type == "interactive":  # 卡片消息
        content = json.dumps(text_content)
    else:
        content = json.dumps({"text": text_content})
    
    data = {
        "receive_id": chat_id,
        "content": content,
        "msg_type": msg_type
    }
    
    # ✅ 关键修复：添加回复功能（飞书官方字段：reply_in_thread）
    if reply_to_message_id:
        # 飞书官方文档：https://open.feishu.cn/document/server-docs/im-v1/message/create
        # 回复指定消息需要使用 "uuid" 字段，并且不需要 reply_in_thread
        data["uuid"] = reply_to_message_id
        logger.info(f"✅ 已添加回复功能: uuid={reply_to_message_id}")
    else:
        logger.warning(f"⚠️  未提供message_id，将使用普通发送模式")
    
    # 打印完整请求数据用于调试
    logger.info(f"📤 发送请求: URL={url}")
    logger.info(f"📤 发送数据: {json.dumps(data, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result.get("code") == 0:
            logger.info(f"成功发送消息到 {chat_id}")
            return True
        else:
            logger.error(f"发送消息失败：{result}")
            return False
    except Exception as e:
        logger.error(f"发送消息异常：{e}")
        return False

# 3. 发送飞书交互卡片
def send_feishu_card_message(chat_id, card_content):
    """发送飞书交互卡片"""
    token = get_feishu_token()
    if not token:
        return False
    
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "receive_id": chat_id,
        "content": json.dumps(card_content),
        "msg_type": "interactive"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result.get("code") == 0:
            logger.info(f"成功发送卡片到 {chat_id}")
            return True
        else:
            logger.error(f"发送卡片失败：{result}")
            return False
    except Exception as e:
        logger.error(f"发送卡片异常：{e}")
        return False

# 3.5 获取飞书群聊历史消息（方案3核心功能）
def get_feishu_chat_history(chat_id, limit=20):
    """从飞书API获取群聊历史消息（使用消息列表API）"""
    token = get_feishu_token()
    if not token:
        logger.error("无法获取Token，无法读取历史消息")
        return []
    
    # ✅ 修复：使用 im/v1/messages 的 list 方法（批量获取消息）
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {
        "container_id_type": "chat",
        "container_id": chat_id,
        "page_size": min(limit, 50),  # 飞书限制最多50条
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        result = response.json()  # 先解析JSON
        
        # 打印详细错误信息用于调试
        if result.get("code") != 0:
            logger.error(f"❌ 飞书API返回错误: code={result.get('code')}, msg={result.get('msg')}")
            logger.error(f"请求URL: {url}")
            logger.error(f"请求参数: {params}")
            
            # ✅ 权限不足时降级：返回空历史，但不报错
            error_code = result.get("code")
            if error_code in [99991663, 99991401, 99991400]:  # 权限相关错误码
                logger.warning(f"⚠️  机器人缺少读取消息权限（code={error_code}），将使用空上下文")
                return []  # 降级：返回空历史
            else:
                return []
        
        messages = result.get("data", {}).get("items", [])
        logger.info(f"📥 飞书API返回 {len(messages)} 条原始消息")
        
        # 解析消息，提取对话历史
        history = []
        for idx, msg in enumerate(messages):
            try:
                msg_type = msg.get("msg_type")
                
                # ✅ 修复：sender 也可能是字符串
                sender = msg.get("sender", {})
                if isinstance(sender, str):
                    sender = json.loads(sender)
                
                sender_id_obj = sender.get("id", {})
                if isinstance(sender_id_obj, str):
                    sender_id_obj = json.loads(sender_id_obj)
                
                sender_id = sender_id_obj.get("open_id", "unknown")
                
                # 只处理文本消息
                if msg_type == "text":
                    # ✅ 修复：body 可能是字符串或对象
                    body = msg.get("body", {})
                    if isinstance(body, str):
                        body = json.loads(body)
                    
                    content_str = body.get("content", "{}")
                    if isinstance(content_str, str):
                        content = json.loads(content_str)
                    else:
                        content = content_str
                    
                    text = content.get("text", "")
                    
                    if text:
                        # 判断是用户还是机器人
                        is_bot = sender_id.startswith("cli_") or sender_id == FEISHU_CONFIG.get("app_id")
                        role = "assistant" if is_bot else "user"
                        
                        history.append({
                            "role": role,
                            "content": text
                        })
                        logger.debug(f"✅ 解析成功 [{idx+1}/{len(messages)}]: role={role}, text={text[:30]}...")
            except Exception as e:
                logger.warning(f"解析消息失败 [{idx+1}/{len(messages)}]：{e}，msg_id={msg.get('message_id', 'unknown')[:20]}")
                continue
        
        logger.info(f"✅ 从飞书获取到 {len(history)} 条历史消息")
        return history
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ HTTP错误: {e.response.status_code} - {e.response.text[:200]}")
        return []
    except Exception as e:
        logger.error(f"获取飞书历史消息异常：{e}")
        return []

# 4. 调用Qoder智能体获取回复
def get_qoder_reply(user_message, user_id=None, chat_id=None, history=None):
    """调用Qoder智能体API获取回复（带自动Fallback）"""
    
    # 检查是否配置了有效的Qoder端点
    qoder_endpoint = QODER_CONFIG.get("api_endpoint")
    
    # 如果没有配置端点，使用简单模式
    if not qoder_endpoint:
        logger.info("Qoder未配置，使用本地回复模式")
        return get_simple_reply(user_message)
    
    # 尝试调用Qoder API（包括本地服务）
    try:
        headers = {
            "Content-Type": "application/json"
        }
        
        # 如果配置了API Key，添加到headers
        if QODER_CONFIG.get('api_key'):
            headers["Authorization"] = f"Bearer {QODER_CONFIG['api_key']}"
        
        data = {
            "message": user_message,
            "user_id": user_id,
            "chat_id": chat_id,
            "history": history or [],  # 传递对话历史
            "context": {
                "platform": "feishu",
                "source": "feishu_bot"
            }
        }
        
        logger.info(f"调用Qoder API: {qoder_endpoint}")
        response = requests.post(
            qoder_endpoint,
            headers=headers,
            json=data,
            timeout=70  # 给 Qoder 60s 超时 + 余量
        )
        response.raise_for_status()
        result = response.json()
        
        # 根据您的Qoder API响应格式调整
        reply = result.get("reply") or result.get("response") or result.get("answer")
        if reply:
            logger.info(f"✅ Qoder API返回成功")
            return reply
        else:
            logger.warning(f"Qoder API返回格式异常: {result}")
            return get_simple_reply(user_message)
            
    except requests.exceptions.ConnectionError as e:
        logger.error(f"⚠️  无法连接到Qoder服务: {qoder_endpoint}，自动降级到本地模式")
        logger.error(f"连接错误详情: {str(e)[:100]}")
        return get_simple_reply(user_message)
    except requests.exceptions.Timeout as e:
        logger.error(f"⚠️  Qoder服务超时，自动降级到本地模式")
        return get_simple_reply(user_message)
    except Exception as e:
        logger.error(f"⚠️  调用Qoder智能体失败: {e}，自动降级到本地模式")
        return get_simple_reply(user_message)

def get_simple_reply(user_message):
    """简单的回复逻辑（当Qoder不可用时）"""
    # 基础的关键词回复
    message_lower = user_message.lower().strip()
    
    if any(word in message_lower for word in ['你好', 'hello', 'hi', '您好']):
        return "你好！我是飞书机器人助手。\n\n目前我处于简单回复模式。要启用完整的AI功能，请配置Qoder智能体服务。\n\n您可以：\n1. 设置环境变量 QODER_API_ENDPOINT\n2. 重启机器人服务"
    
    elif any(word in message_lower for word in ['帮助', 'help', '功能']):
        return "我是一个飞书机器人，可以：\n\n✅ 接收和回复消息\n✅ 支持AI智能对话（需配置Qoder）\n✅ 24小时在线服务\n\n当前状态：简单回复模式"
    
    elif any(word in message_lower for word in ['测试', 'test']):
        return "✅ 测试成功！\n\n机器人运行正常，可以正常接收和发送消息。\n\n如需启用AI对话功能，请配置Qoder智能体。"
    
    else:
        return f"收到您的消息：{user_message}\n\n我目前处于简单回复模式。要使用完整的AI对话功能，请联系管理员配置Qoder智能体服务。"

# 5. 飞书事件回调接口
@app.route("/feishu/callback", methods=["POST"])
def feishu_callback():
    """接收飞书事件回调"""
    try:
        # 获取请求数据
        event_data = request.get_json()
        
        # 打印完整的请求数据用于调试
        logger.info(f"收到飞书请求：{json.dumps(event_data, ensure_ascii=False)[:500]}")
        
        # 处理URL验证（飞书首次配置回调地址时会发送）
        if event_data.get("type") == "url_verification":
            challenge = event_data.get("challenge")
            logger.info("收到飞书URL验证请求")
            return jsonify({"challenge": challenge})
        
        # 验证Token（兼容新旧版本）
        # 事件订阅 2.0 的 token 在 header 中
        token_to_verify = event_data.get("token") or event_data.get("header", {}).get("token")
        
        if token_to_verify and token_to_verify != FEISHU_CONFIG["verification_token"]:
            logger.warning(f"无效的verification_token: 收到={token_to_verify}, 期望={FEISHU_CONFIG['verification_token']}")
            return jsonify({"code": 1, "msg": "invalid token"}), 401
        
        # 处理消息事件
        if event_data.get("header", {}).get("event_type") == "im.message.receive_v1":
            event_id = event_data.get("header", {}).get("event_id")
                    
            # ⚠️ 检查事件是否已处理过（防止重复处理）
            if event_id and is_event_processed(event_id):
                logger.warning(f"⚠️ 事件 {event_id} 已处理过，忽略重复事件")
                return jsonify({"code": 0, "msg": "success"})
                    
            # 标记事件为已处理
            if event_id:
                mark_event_processed(event_id)
                    
            event = event_data.get("event", {})
            message = event.get("message", {})
            sender = event.get("sender", {})
                    
            # 获取消息内容
            chat_id = message.get("chat_id")
            message_type = message.get("message_type")
            message_id = message.get("message_id")  # 添加message_id的获取
            create_time = message.get("create_time")  # 消息创建时间（毫秒）
            content = json.loads(message.get("content", "{}"))
            
            # ✅ 关键修复：正确获取用户ID（群聊场景优先使用 open_id）
            sender_id_obj = sender.get("sender_id", {})
            sender_id = (
                sender_id_obj.get("open_id") or  # 群聊场景：优先使用 open_id
                sender_id_obj.get("user_id") or  # 私聊场景：使用 user_id
                chat_id  # 兜底：使用 chat_id
            )
            
            logger.info(f"收到消息：chat_id={chat_id}, sender_id={sender_id}, type={message_type}")
                        
            # ✅ 关键检查：只处理最近 2 分钟内的消息（防止重启后处理旧消息）
            if create_time:
                current_time = int(time.time() * 1000)  # 当前时间（毫秒）
                message_age = (current_time - int(create_time)) / 1000  # 消息年龄（秒）
                if message_age > 120:  # 2 分钟 = 120 秒
                    logger.warning(f"⚠️ 消息过旧（{message_age:.0f}秒前），忽略处理")
                    return jsonify({"code": 0, "msg": "success"})
            
            # ⚠️ 重要：按message_id也进行去重（防止旧消息的重复）
            if message_id and message_id in processed_messages:
                logger.warning(f"⚠️ 消息 {message_id} 已处理过，忽略伜旧消息")
                return jsonify({"code": 0, "msg": "success"})
            
            # 标记消息为已处理
            if message_id:
                processed_messages.add(message_id)
            
            # ⚠️ 重要：立即返回200响应，防止飞书重试（这是导致重复的根本原因）
            # 必须在处理消息之前返回，避免超时
            response_obj = jsonify({"code": 0, "msg": "success"})
            
            # 检查用户权限
            if sender_id and not check_user_permission(sender_id):
                logger.warning(f"用户 {sender_id} 无权限使用机器人")
                send_feishu_text_message(chat_id, "抱歉，您没有权限使用该机器人。请联系管理员添加权限。")
                return response_obj
            
            # 处理不同类型的消息
            if message_type == "text":
                # 处理文本消息
                user_text = content.get("text", "").strip()
                
                if user_text:
                    # ✅ 关键修复：启动后台线程处理，立即返回响应，并传递message_id
                    thread = Thread(target=process_message_async, args=(chat_id, sender_id, user_text, message_id))
                    thread.daemon = True  # 守护线程，主程序退出时自动结束
                    thread.start()
                    logger.info(f"✅ 已启动异步处理线程，立即返回飞书")
            
            elif message_type == "image":
                # 处理图片消息
                image_key = content.get("image_key", "")
                logger.info(f"收到图片消息: {image_key}")
                send_feishu_text_message(chat_id, "🖼️ 我收到了您的图片，但目前还不支持图片分析功能。请用文字描述您的问题。")
            
            elif message_type == "file":
                # 处理文件消息
                file_key = content.get("file_key", "")
                file_name = content.get("file_name", "未知文件")
                logger.info(f"收到文件: {file_name} ({file_key})")
                send_feishu_text_message(chat_id, f"📄 我收到了您的文件「{file_name}」，但目前还不支持文件分析功能。")
            
            elif message_type == "audio":
                # 处理音频消息
                logger.info("收到音频消息")
                send_feishu_text_message(chat_id, "🎤 我收到了您的音频，但目前还不支持语音识别功能。请用文字输入。")
            
            else:
                # 其他类型消息
                logger.info(f"收到不支持的消息类型: {message_type}")
                send_feishu_text_message(chat_id, f"收到您的{message_type}类型消息，但目前只支持文字消息。请用文字与我交流。")
            
            # 返回200响应
            return response_obj
        
        # 飞书要求回调必须返回200和空JSON
        return jsonify({"code": 0, "msg": "success"})
    
    except Exception as e:
        logger.error(f"处理回调异常：{e}", exc_info=True)
        return jsonify({"code": 1, "msg": str(e)}), 500

# 6. 健康检查接口
@app.route("/health", methods=["GET"])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "ok",
        "service": "feishu-qoder-bot",
        "timestamp": int(time.time())
    })

# 7. 测试发送消息接口
@app.route("/test/send", methods=["POST"])
def test_send_message():
    """测试发送消息接口"""
    data = request.get_json()
    chat_id = data.get("chat_id")
    message = data.get("message", "测试消息")
    
    if not chat_id:
        return jsonify({"error": "缺少chat_id参数"}), 400
    
    success = send_feishu_text_message(chat_id, message)
    
    if success:
        return jsonify({"status": "success", "message": "发送成功"})
    else:
        return jsonify({"status": "error", "message": "发送失败"}), 500

# 8. 查看对话历史
@app.route("/history/<user_id>", methods=["GET"])
def get_history(user_id):
    """获取用户的对话历史"""
    limit = request.args.get("limit", 10, type=int)
    history = get_conversation_history(user_id, limit)
    return jsonify({
        "user_id": user_id,
        "history_count": len(history),
        "history": history
    })

# 9. 清空对话历史
@app.route("/history/<user_id>", methods=["DELETE"])
def clear_history(user_id):
    """清空用户的对话历史"""
    if user_id in conversation_history:
        del conversation_history[user_id]
        return jsonify({"status": "success", "message": f"已清空用户 {user_id} 的对话历史"})
    else:
        return jsonify({"status": "success", "message": "该用户没有对话历史"})

# 10. 统计信息
@app.route("/stats", methods=["GET"])
def get_stats():
    """获取系统统计信息"""
    total_users = len(conversation_history)
    total_messages = sum(len(history) for history in conversation_history.values())
    
    return jsonify({
        "total_users": total_users,
        "total_messages": total_messages,
        "active_users": list(conversation_history.keys())[:10],  # 最近10个活跃用户
        "qoder_endpoint": QODER_CONFIG.get("api_endpoint"),
        "permissions_enabled": ALLOWED_USERS is not None,
        "processed_events_count": len(processed_events)
    })

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("飞书机器人服务启动中...")
    logger.info("=" * 50)
    
    # 从环境变量获取端口
    port = int(os.getenv("SERVER_PORT", "5004"))
    logger.info(f"服务将在端口 {port} 启动")
    
    # 启动Flask应用
    app.run(host="0.0.0.0", port=port, debug=False)
