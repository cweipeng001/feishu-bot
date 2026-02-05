#!/usr/bin/env python3
"""
飞书 OAuth 2.0 Token 管理模块
用于管理 user_access_token 的获取、存储和自动刷新
"""

import os
import json
import time
import logging
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 飞书 OAuth 配置
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")

# OAuth 相关 URL
FEISHU_OAUTH_URL = "https://open.feishu.cn/open-apis/authen/v1/authorize"
FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v1/oidc/access_token"
FEISHU_REFRESH_URL = "https://open.feishu.cn/open-apis/authen/v1/oidc/refresh_access_token"
FEISHU_USER_INFO_URL = "https://open.feishu.cn/open-apis/authen/v1/user_info"

# Token 存储路径
TOKEN_STORAGE_PATH = Path(__file__).parent / "feishu_user_token.json"

# Token 提前刷新时间（秒），在过期前10分钟刷新
TOKEN_REFRESH_BUFFER = 600


class FeishuAuthManager:
    """飞书 OAuth 认证管理器"""
    
    def __init__(self, app_id: str = None, app_secret: str = None, 
                 redirect_uri: str = None, storage_path: Path = None):
        """
        初始化认证管理器
        
        Args:
            app_id: 飞书应用 ID
            app_secret: 飞书应用 Secret
            redirect_uri: OAuth 回调地址
            storage_path: Token 存储路径
        """
        self.app_id = app_id or FEISHU_APP_ID
        self.app_secret = app_secret or FEISHU_APP_SECRET
        self.redirect_uri = redirect_uri or os.getenv("FEISHU_OAUTH_REDIRECT_URI", "http://127.0.0.1:5004/auth/feishu/callback")
        self.storage_path = storage_path or TOKEN_STORAGE_PATH
        
        # 内存缓存
        self._token_cache: Optional[Dict[str, Any]] = None
        
        # 加载已存储的 Token
        self._load_token_from_storage()
    
    def generate_auth_url(self, state: str = None) -> str:
        """
        生成 OAuth 授权链接
        
        Args:
            state: 可选的状态参数，用于防止 CSRF 攻击
            
        Returns:
            授权链接 URL
        """
        if not state:
            state = f"feishu_auth_{int(time.time())}"
        
        params = {
            "app_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state,
            # 添加文档搜索权限
            "scope": "search:docs:read wiki:wiki:readonly"
            # 注意：offline_access 需要应用启用网页能力，暂时不使用
            # token 过期后需重新授权（约2小时）
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        auth_url = f"{FEISHU_OAUTH_URL}?{query_string}"
        
        logger.info(f"生成授权链接: {auth_url}")
        return auth_url
    
    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        用授权码换取 access_token
        
        Args:
            code: OAuth 授权码
            
        Returns:
            Token 数据字典
        """
        # 首先获取 app_access_token
        app_token = self._get_app_access_token()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {app_token}"
        }
        
        payload = {
            "grant_type": "authorization_code",
            "code": code
        }
        
        try:
            response = requests.post(FEISHU_TOKEN_URL, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                error_msg = result.get("msg", "未知错误")
                logger.error(f"换取 Token 失败: {error_msg}")
                raise Exception(f"换取 Token 失败: {error_msg}")
            
            token_data = result.get("data", {})
            
            # 添加获取时间戳，用于计算过期时间
            token_data["obtained_at"] = int(time.time())
            
            # 保存到存储
            self._save_token_to_storage(token_data)
            
            logger.info(f"✅ 成功获取 user_access_token，有效期: {token_data.get('expires_in', 0)}秒")
            return token_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求飞书 API 失败: {e}")
            raise
    
    def get_valid_user_token(self) -> Optional[str]:
        """
        获取有效的 user_access_token
        如果 Token 即将过期，自动刷新
        
        Returns:
            有效的 user_access_token，如果没有则返回 None
        """
        if not self._token_cache:
            logger.warning("⚠️ 没有缓存的 Token，请先完成 OAuth 授权")
            return None
        
        # 检查是否需要刷新
        if self._is_token_expiring_soon():
            logger.info("🔄 Token 即将过期，正在刷新...")
            if not self._refresh_token():
                logger.error("❌ Token 刷新失败")
                return None
        
        return self._token_cache.get("access_token")
    
    def _is_token_expiring_soon(self) -> bool:
        """检查 Token 是否即将过期"""
        if not self._token_cache:
            return True
        
        obtained_at = self._token_cache.get("obtained_at", 0)
        expires_in = self._token_cache.get("expires_in", 0)
        
        # 计算剩余有效时间
        elapsed = int(time.time()) - obtained_at
        remaining = expires_in - elapsed
        
        logger.debug(f"Token 剩余有效时间: {remaining}秒")
        
        return remaining < TOKEN_REFRESH_BUFFER
    
    def _refresh_token(self) -> bool:
        """
        刷新 access_token
        
        Returns:
            是否刷新成功
        """
        refresh_token = self._token_cache.get("refresh_token")
        if not refresh_token:
            logger.error("❌ 没有 refresh_token，无法刷新")
            return False
        
        # 获取 app_access_token
        app_token = self._get_app_access_token()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {app_token}"
        }
        
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        try:
            response = requests.post(FEISHU_REFRESH_URL, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                error_msg = result.get("msg", "未知错误")
                logger.error(f"刷新 Token 失败: {error_msg}")
                return False
            
            token_data = result.get("data", {})
            token_data["obtained_at"] = int(time.time())
            
            # 保存新的 Token
            self._save_token_to_storage(token_data)
            
            logger.info(f"✅ Token 刷新成功，新有效期: {token_data.get('expires_in', 0)}秒")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"刷新 Token 请求失败: {e}")
            return False
    
    def _get_app_access_token(self) -> str:
        """获取应用级别的 access_token"""
        url = "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal"
        
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                raise Exception(f"获取 app_access_token 失败: {result.get('msg')}")
            
            return result.get("app_access_token", "")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取 app_access_token 失败: {e}")
            raise
    
    def _load_token_from_storage(self):
        """从存储加载 Token"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self._token_cache = json.load(f)
                logger.info(f"✅ 从存储加载 Token 成功")
            except Exception as e:
                logger.error(f"加载 Token 失败: {e}")
                self._token_cache = None
        else:
            logger.info("📝 Token 存储文件不存在，需要进行 OAuth 授权")
            self._token_cache = None
    
    def _save_token_to_storage(self, token_data: Dict[str, Any]):
        """保存 Token 到存储"""
        try:
            # 更新内存缓存
            self._token_cache = token_data
            
            # 保存到文件
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Token 已保存到: {self.storage_path}")
            
        except Exception as e:
            logger.error(f"保存 Token 失败: {e}")
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """
        获取当前授权用户的信息
        
        Returns:
            用户信息字典
        """
        user_token = self.get_valid_user_token()
        if not user_token:
            return None
        
        headers = {
            "Authorization": f"Bearer {user_token}"
        }
        
        try:
            response = requests.get(FEISHU_USER_INFO_URL, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                logger.error(f"获取用户信息失败: {result.get('msg')}")
                return None
            
            return result.get("data", {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取用户信息请求失败: {e}")
            return None
    
    def is_authorized(self) -> bool:
        """检查是否已完成授权"""
        return self._token_cache is not None and "access_token" in self._token_cache
    
    def get_token_status(self) -> Dict[str, Any]:
        """
        获取当前 Token 的状态信息
        
        Returns:
            Token 状态字典
        """
        if not self._token_cache:
            return {
                "authorized": False,
                "message": "未授权，请先完成 OAuth 授权流程"
            }
        
        obtained_at = self._token_cache.get("obtained_at", 0)
        expires_in = self._token_cache.get("expires_in", 0)
        refresh_expires_in = self._token_cache.get("refresh_expires_in", 0)
        
        elapsed = int(time.time()) - obtained_at
        access_remaining = max(0, expires_in - elapsed)
        refresh_remaining = max(0, refresh_expires_in - elapsed)
        
        return {
            "authorized": True,
            "access_token_remaining_seconds": access_remaining,
            "access_token_remaining_minutes": round(access_remaining / 60, 1),
            "refresh_token_remaining_days": round(refresh_remaining / 86400, 1),
            "is_expiring_soon": access_remaining < TOKEN_REFRESH_BUFFER,
            "obtained_at": datetime.fromtimestamp(obtained_at).isoformat() if obtained_at else None
        }


# 全局单例实例
_auth_manager: Optional[FeishuAuthManager] = None


def get_auth_manager() -> FeishuAuthManager:
    """获取全局认证管理器实例"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = FeishuAuthManager()
    return _auth_manager


# 便捷函数
def get_user_access_token() -> Optional[str]:
    """获取有效的 user_access_token（便捷函数）"""
    return get_auth_manager().get_valid_user_token()


def is_user_authorized() -> bool:
    """检查用户是否已授权（便捷函数）"""
    return get_auth_manager().is_authorized()


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("🔐 飞书 OAuth 认证管理器测试")
    print("=" * 60)
    
    manager = get_auth_manager()
    
    # 检查当前状态
    status = manager.get_token_status()
    print(f"\n当前授权状态: {json.dumps(status, ensure_ascii=False, indent=2)}")
    
    if not status["authorized"]:
        # 生成授权链接
        auth_url = manager.generate_auth_url()
        print(f"\n请在浏览器中访问以下链接完成授权:")
        print(f"  {auth_url}")
        print("\n授权完成后，系统将获得访问飞书文档的能力。")
    else:
        # 测试获取用户信息
        print("\n正在获取当前授权用户信息...")
        user_info = manager.get_user_info()
        if user_info:
            print(f"用户名: {user_info.get('name', '未知')}")
            print(f"用户ID: {user_info.get('open_id', '未知')}")
        
        # 测试获取 Token
        token = manager.get_valid_user_token()
        if token:
            print(f"\n✅ 成功获取 user_access_token (前20字符): {token[:20]}...")
        else:
            print("\n❌ 获取 Token 失败")
