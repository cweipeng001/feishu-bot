#!/usr/bin/env python3
"""
飞书机器人双模式运行管理器
支持 Qoder MCP 模式和独立运行模式的无缝切换
"""

import os
import sys
import json
import logging
import threading
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class RuntimeMode:
    """运行模式配置"""
    name: str
    description: str
    mcp_source: str  # 'qoder' 或 'official' 或 'rest_api'
    auto_fallback: bool
    health_check_interval: int

class HybridBotManager:
    """混合模式机器人管理器"""
    
    def __init__(self):
        self.modes = self._init_modes()
        self.current_mode = self._determine_initial_mode()
        self.health_thread: Optional[threading.Thread] = None
        self.running = False
        
    def _init_modes(self) -> Dict[str, RuntimeMode]:
        """初始化运行模式"""
        return {
            "qoder_mcp": RuntimeMode(
                name="qoder_mcp",
                description="使用 Qoder 中配置的飞书 MCP 服务",
                mcp_source="qoder",
                auto_fallback=True,
                health_check_interval=30
            ),
            "official_mcp": RuntimeMode(
                name="official_mcp", 
                description="使用飞书官方 MCP 服务（需要特殊授权）",
                mcp_source="official",
                auto_fallback=True,
                health_check_interval=60
            ),
            "rest_api": RuntimeMode(
                name="rest_api",
                description="使用飞书 REST API（稳定可靠）",
                mcp_source="rest_api", 
                auto_fallback=False,
                health_check_interval=120
            )
        }
    
    def _determine_initial_mode(self) -> RuntimeMode:
        """确定初始运行模式"""
        # 检查环境变量配置
        forced_mode = os.getenv("BOT_RUNTIME_MODE")
        if forced_mode and forced_mode in self.modes:
            logger.info(f"🎯 强制使用运行模式: {forced_mode}")
            return self.modes[forced_mode]
        
        # 检查 Qoder MCP 配置文件是否存在
        qoder_config_path = os.path.expanduser("~/.qoder/settings.json")
        if os.path.exists(qoder_config_path):
            try:
                with open(qoder_config_path, 'r') as f:
                    qoder_config = json.load(f)
                if "mcpServers" in qoder_config and "feishu" in qoder_config["mcpServers"]:
                    logger.info("✅ 检测到 Qoder 中配置的飞书 MCP 服务")
                    return self.modes["qoder_mcp"]
            except Exception as e:
                logger.warning(f"⚠️ 读取 Qoder 配置失败: {e}")
        
        # 检查官方 MCP 配置
        official_mcp_url = os.getenv("FEISHU_OFFICIAL_MCP_URL")
        if official_mcp_url:
            logger.info("✅ 检测到飞书官方 MCP 配置")
            return self.modes["official_mcp"]
        
        # 默认使用 REST API 模式（最稳定）
        logger.info("🔄 默认使用 REST API 模式（最稳定）")
        return self.modes["rest_api"]
    
    def start_health_monitoring(self):
        """启动健康监控"""
        if self.health_thread and self.health_thread.is_alive():
            return
            
        self.running = True
        self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_thread.start()
        logger.info(f"✅ 启动健康监控 (模式: {self.current_mode.name})")
    
    def stop_health_monitoring(self):
        """停止健康监控"""
        self.running = False
        if self.health_thread:
            self.health_thread.join(timeout=5)
        logger.info("⏹️ 停止健康监控")
    
    def _health_check_loop(self):
        """健康检查循环"""
        while self.running:
            try:
                if not self._check_current_mode_health():
                    if self.current_mode.auto_fallback:
                        self._attempt_fallback()
                    else:
                        logger.error(f"❌ 当前模式 {self.current_mode.name} 健康检查失败且无备用方案")
                        
            except Exception as e:
                logger.error(f"❌ 健康检查异常: {e}")
            
            time.sleep(self.current_mode.health_check_interval)
    
    def _check_current_mode_health(self) -> bool:
        """检查当前模式健康状态"""
        try:
            if self.current_mode.name == "qoder_mcp":
                return self._check_qoder_mcp_health()
            elif self.current_mode.name == "official_mcp":
                return self._check_official_mcp_health()
            elif self.current_mode.name == "rest_api":
                return self._check_rest_api_health()
            return False
        except Exception as e:
            logger.error(f"❌ 健康检查失败: {e}")
            return False
    
    def _check_qoder_mcp_health(self) -> bool:
        """检查 Qoder MCP 健康状态"""
        # 检查 Qoder 配置文件
        qoder_config_path = os.path.expanduser("~/.qoder/settings.json")
        if not os.path.exists(qoder_config_path):
            logger.warning("⚠️ Qoder 配置文件不存在")
            return False
            
        # 检查飞书 MCP 配置
        try:
            with open(qoder_config_path, 'r') as f:
                config = json.load(f)
            if "mcpServers" not in config or "feishu" not in config["mcpServers"]:
                logger.warning("⚠️ Qoder 中未配置飞书 MCP 服务")
                return False
            logger.info("✅ Qoder MCP 配置正常")
            return True
        except Exception as e:
            logger.error(f"❌ 检查 Qoder MCP 配置失败: {e}")
            return False
    
    def _check_official_mcp_health(self) -> bool:
        """检查官方 MCP 健康状态"""
        # 这个模式需要特殊授权，暂时标记为需要人工确认
        logger.info("ℹ️ 官方 MCP 模式需要通过 Qoder 客户端授权确认")
        return True  # 假设配置正确
    
    def _check_rest_api_health(self) -> bool:
        """检查 REST API 健康状态"""
        try:
            from rest_api_client import search_feishu_knowledge_real
            # 简单测试搜索功能
            result = search_feishu_knowledge_real("测试", 1)
            logger.info("✅ REST API 健康检查通过")
            return True
        except Exception as e:
            logger.error(f"❌ REST API 健康检查失败: {e}")
            return False
    
    def _attempt_fallback(self):
        """尝试降级到备用模式"""
        fallback_order = ["rest_api", "official_mcp", "qoder_mcp"]
        
        current_index = fallback_order.index(self.current_mode.name)
        for i in range(current_index + 1, len(fallback_order)):
            fallback_mode = self.modes[fallback_order[i]]
            if self._test_mode_availability(fallback_mode):
                logger.info(f"🔄 降级到备用模式: {fallback_mode.name}")
                self.current_mode = fallback_mode
                return
        
        logger.error("❌ 无可用的备用模式")
    
    def _test_mode_availability(self, mode: RuntimeMode) -> bool:
        """测试模式可用性"""
        try:
            if mode.name == "rest_api":
                return self._check_rest_api_health()
            elif mode.name == "official_mcp":
                return self._check_official_mcp_health()
            elif mode.name == "qoder_mcp":
                return self._check_qoder_mcp_health()
            return False
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前运行状态"""
        return {
            "current_mode": self.current_mode.name,
            "mode_description": self.current_mode.description,
            "mcp_source": self.current_mode.mcp_source,
            "health_monitoring": self.running,
            "available_modes": list(self.modes.keys()),
            "timestamp": time.time()
        }
    
    def switch_mode(self, mode_name: str) -> bool:
        """切换运行模式"""
        if mode_name not in self.modes:
            logger.error(f"❌ 无效的模式名称: {mode_name}")
            return False
            
        new_mode = self.modes[mode_name]
        if self._test_mode_availability(new_mode):
            old_mode = self.current_mode.name
            self.current_mode = new_mode
            logger.info(f"🔄 模式切换: {old_mode} → {new_mode.name}")
            return True
        else:
            logger.error(f"❌ 模式 {mode_name} 不可用")
            return False

# 全局实例
_bot_manager: Optional[HybridBotManager] = None

def get_bot_manager() -> HybridBotManager:
    """获取机器人管理器实例"""
    global _bot_manager
    if _bot_manager is None:
        _bot_manager = HybridBotManager()
    return _bot_manager

def start_hybrid_bot():
    """启动混合模式机器人"""
    manager = get_bot_manager()
    manager.start_health_monitoring()
    return manager

def stop_hybrid_bot():
    """停止混合模式机器人"""
    manager = get_bot_manager()
    manager.stop_health_monitoring()

# 集成到主程序的装饰器
def with_hybrid_support(func):
    """为函数添加混合模式支持的装饰器"""
    def wrapper(*args, **kwargs):
        manager = get_bot_manager()
        # 可以在这里添加模式相关的逻辑
        return func(*args, **kwargs)
    return wrapper

# 测试函数
def test_hybrid_manager():
    """测试混合管理器"""
    print("🚀 测试混合模式机器人管理器")
    print("=" * 50)
    
    manager = get_bot_manager()
    
    print(f"🎯 当前模式: {manager.current_mode.name}")
    print(f"📝 模式描述: {manager.current_mode.description}")
    print(f"🔌 MCP 源: {manager.current_mode.mcp_source}")
    
    print(f"\n📋 可用模式:")
    for mode_name, mode in manager.modes.items():
        status = "✓" if mode_name == manager.current_mode.name else "○"
        print(f"  {status} {mode_name}: {mode.description}")
    
    print(f"\n📊 当前状态:")
    status = manager.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # 测试模式切换
    print(f"\n🔄 测试模式切换...")
    if manager.switch_mode("rest_api"):
        print(f"✅ 成功切换到 REST API 模式")
    else:
        print(f"❌ 切换失败")

if __name__ == "__main__":
    test_hybrid_manager()