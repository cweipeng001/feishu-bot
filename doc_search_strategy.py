#!/usr/bin/env python3
"""
飞书文档搜索策略管理器
支持多种文档搜索方案的切换和管理
"""

import os
import logging
from enum import Enum
from typing import Optional, List
from dataclasses import dataclass

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

class DocSearchStrategy(Enum):
    """文档搜索策略枚举"""
    REST_API = "rest_api"           # REST API 方式（当前使用）
    OFFICIAL_MCP = "official_mcp"   # 飞书官方 MCP 服务
    OPENAPI_MCP = "openapi_mcp"     # 自建 OpenAPI MCP 服务
    SIMPLE_CLIENT = "simple_client" # 简单客户端（备用）

@dataclass
class SearchStrategyConfig:
    """搜索策略配置"""
    strategy: DocSearchStrategy
    enabled: bool = True
    priority: int = 1  # 数字越小优先级越高
    fallback_allowed: bool = True  # 是否允许降级到其他策略

class DocSearchManager:
    """文档搜索策略管理器"""
    
    def __init__(self):
        self.strategies = self._load_strategies()
        self.current_strategy = self._determine_best_strategy()
        logger.info(f"🎯 当前使用文档搜索策略: {self.current_strategy.value}")
    
    def _load_strategies(self) -> List[SearchStrategyConfig]:
        """加载所有可用的搜索策略"""
        strategies = []
        
        # REST API 策略（最高优先级）
        strategies.append(SearchStrategyConfig(
            strategy=DocSearchStrategy.REST_API,
            enabled=True,
            priority=1,
            fallback_allowed=True
        ))
        
        # 官方 MCP 策略
        official_mcp_url = os.getenv("FEISHU_OFFICIAL_MCP_URL")
        strategies.append(SearchStrategyConfig(
            strategy=DocSearchStrategy.OFFICIAL_MCP,
            enabled=bool(official_mcp_url),
            priority=2,
            fallback_allowed=True
        ))
        
        # OpenAPI MCP 策略
        app_id = os.getenv("FEISHU_APP_ID")
        app_secret = os.getenv("FEISHU_APP_SECRET")
        strategies.append(SearchStrategyConfig(
            strategy=DocSearchStrategy.OPENAPI_MCP,
            enabled=bool(app_id and app_secret),
            priority=3,
            fallback_allowed=True
        ))
        
        # 简单客户端策略（最低优先级，备用）
        strategies.append(SearchStrategyConfig(
            strategy=DocSearchStrategy.SIMPLE_CLIENT,
            enabled=True,
            priority=4,
            fallback_allowed=False  # 最后兜底，不允许再降级
        ))
        
        return sorted(strategies, key=lambda x: x.priority)
    
    def _determine_best_strategy(self) -> DocSearchStrategy:
        """确定最佳搜索策略"""
        # 检查是否有强制指定的策略
        forced_strategy = os.getenv("FEISHU_DOC_SEARCH_STRATEGY")
        if forced_strategy:
            try:
                return DocSearchStrategy(forced_strategy.lower())
            except ValueError:
                logger.warning(f"⚠️ 无效的强制策略: {forced_strategy}")
        
        # 按优先级选择第一个启用的策略
        for strategy_config in self.strategies:
            if strategy_config.enabled:
                return strategy_config.strategy
        
        # 如果都没有启用，使用简单客户端作为最后兜底
        return DocSearchStrategy.SIMPLE_CLIENT
    
    def get_current_strategy(self) -> DocSearchStrategy:
        """获取当前使用的策略"""
        return self.current_strategy
    
    def switch_strategy(self, strategy: DocSearchStrategy) -> bool:
        """
        切换搜索策略
        
        Args:
            strategy: 要切换到的策略
            
        Returns:
            是否切换成功
        """
        # 检查策略是否可用
        strategy_config = next((s for s in self.strategies if s.strategy == strategy), None)
        if not strategy_config or not strategy_config.enabled:
            logger.error(f"❌ 策略 {strategy.value} 不可用")
            return False
        
        logger.info(f"🔄 切换文档搜索策略: {self.current_strategy.value} → {strategy.value}")
        self.current_strategy = strategy
        return True
    
    def get_available_strategies(self) -> List[SearchStrategyConfig]:
        """获取所有可用的策略"""
        return [s for s in self.strategies if s.enabled]
    
    def get_strategy_info(self) -> dict:
        """获取策略信息"""
        return {
            "current_strategy": self.current_strategy.value,
            "available_strategies": [s.strategy.value for s in self.get_available_strategies()],
            "total_strategies": len(self.strategies)
        }

# 全局实例
_search_manager: Optional[DocSearchManager] = None

def get_search_manager() -> DocSearchManager:
    """获取搜索管理器实例"""
    global _search_manager
    if _search_manager is None:
        _search_manager = DocSearchManager()
    return _search_manager

def get_current_strategy() -> DocSearchStrategy:
    """获取当前搜索策略"""
    return get_search_manager().get_current_strategy()

def switch_search_strategy(strategy: DocSearchStrategy) -> bool:
    """切换搜索策略"""
    return get_search_manager().switch_strategy(strategy)

def get_strategy_info() -> dict:
    """获取策略信息"""
    return get_search_manager().get_strategy_info()

# 便捷函数：根据当前策略执行搜索
def search_documents_adaptive(query: str, count: int = 3) -> List:
    """
    自适应文档搜索（根据当前策略自动选择实现）
    
    Args:
        query: 搜索关键词
        count: 返回结果数量
        
    Returns:
        搜索结果列表
    """
    strategy = get_current_strategy()
    logger.info(f"🔍 使用 {strategy.value} 策略搜索文档: '{query}'")
    
    try:
        if strategy == DocSearchStrategy.REST_API:
            from rest_api_client import search_feishu_knowledge_real
            return search_feishu_knowledge_real(query, count)
            
        elif strategy == DocSearchStrategy.OFFICIAL_MCP:
            from feishu_official_mcp import search_feishu_documents_official
            return search_feishu_documents_official(query, count)
            
        elif strategy == DocSearchStrategy.OPENAPI_MCP:
            from feishu_docs_openapi import search_feishu_knowledge
            return search_feishu_knowledge(query, count)
            
        elif strategy == DocSearchStrategy.SIMPLE_CLIENT:
            from simple_openapi_client import search_feishu_knowledge_simple
            return search_feishu_knowledge_simple(query, count)
            
        else:
            logger.error(f"❌ 未知的搜索策略: {strategy}")
            return []
            
    except Exception as e:
        logger.error(f"❌ {strategy.value} 策略搜索失败: {e}")
        # 如果允许降级，尝试下一个策略
        manager = get_search_manager()
        current_config = next((s for s in manager.strategies if s.strategy == strategy), None)
        if current_config and current_config.fallback_allowed:
            logger.info("🔄 尝试降级到备用策略...")
            # 这里可以实现自动降级逻辑
            pass
        
        return []

# 测试函数
def test_strategy_manager():
    """测试策略管理器"""
    print("🚀 测试文档搜索策略管理器...")
    
    manager = get_search_manager()
    
    print(f"\n🎯 当前策略: {manager.get_current_strategy().value}")
    
    print("\n📋 可用策略:")
    for strategy in manager.get_available_strategies():
        print(f"  - {strategy.strategy.value} (优先级: {strategy.priority})")
    
    print(f"\n📊 策略信息: {manager.get_strategy_info()}")
    
    # 测试策略切换
    print("\n🔄 测试策略切换...")
    if manager.switch_strategy(DocSearchStrategy.OFFICIAL_MCP):
        print(f"✅ 成功切换到: {manager.get_current_strategy().value}")
    else:
        print("❌ 切换失败")

if __name__ == "__main__":
    test_strategy_manager()