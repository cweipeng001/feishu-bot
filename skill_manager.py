#!/usr/bin/env python3
"""
Skill 管理器
负责加载、注册和调用各种技能
"""

import os
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SkillMetadata:
    """Skill 元数据"""
    name: str
    description: str
    handler: Callable
    params_schema: Dict[str, Any]
    enabled: bool = True

class SkillManager:
    """Skill 管理器"""
    
    def __init__(self):
        self.skills: Dict[str, SkillMetadata] = {}
        logger.info("🎯 Skill 管理器初始化")
    
    def register_skill(
        self, 
        name: str, 
        handler: Callable,
        description: str = "",
        params_schema: Dict[str, Any] = None,
        enabled: bool = True
    ):
        """
        注册一个 Skill
        
        Args:
            name: Skill 名称
            handler: Skill 处理函数
            description: Skill 描述
            params_schema: 参数模式定义
            enabled: 是否启用
        """
        skill = SkillMetadata(
            name=name,
            description=description,
            handler=handler,
            params_schema=params_schema or {},
            enabled=enabled
        )
        
        self.skills[name] = skill
        logger.info(f"✅ 注册 Skill: {name} - {description}")
    
    def invoke_skill(self, name: str, params: Dict[str, Any] = None) -> Any:
        """
        调用一个 Skill
        
        Args:
            name: Skill 名称
            params: 调用参数
            
        Returns:
            Skill 执行结果
        """
        if name not in self.skills:
            logger.error(f"❌ Skill 不存在: {name}")
            raise ValueError(f"Skill '{name}' not found")
        
        skill = self.skills[name]
        
        if not skill.enabled:
            logger.warning(f"⚠️  Skill 未启用: {name}")
            return None
        
        logger.info(f"🔧 调用 Skill: {name}")
        
        try:
            # 调用 Skill 处理函数
            params = params or {}
            result = skill.handler(**params)
            logger.info(f"✅ Skill 执行成功: {name}")
            return result
        except Exception as e:
            logger.error(f"❌ Skill 执行失败: {name} - {e}")
            raise
    
    def list_skills(self) -> Dict[str, SkillMetadata]:
        """列出所有已注册的 Skills"""
        return self.skills
    
    def get_skill(self, name: str) -> Optional[SkillMetadata]:
        """获取指定的 Skill 元数据"""
        return self.skills.get(name)
    
    def enable_skill(self, name: str):
        """启用一个 Skill"""
        if name in self.skills:
            self.skills[name].enabled = True
            logger.info(f"✅ 启用 Skill: {name}")
    
    def disable_skill(self, name: str):
        """禁用一个 Skill"""
        if name in self.skills:
            self.skills[name].enabled = False
            logger.info(f"⏸️  禁用 Skill: {name}")

# 全局 Skill 管理器实例
_skill_manager = None

def get_skill_manager() -> SkillManager:
    """获取全局 Skill 管理器实例"""
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = SkillManager()
    return _skill_manager

def invoke_skill(name: str, **params) -> Any:
    """
    快捷函数：调用一个 Skill
    
    Args:
        name: Skill 名称
        **params: 调用参数
        
    Returns:
        Skill 执行结果
    """
    manager = get_skill_manager()
    return manager.invoke_skill(name, params)

# 测试代码
if __name__ == "__main__":
    # 创建管理器
    manager = get_skill_manager()
    
    # 注册测试 Skill
    def test_skill(message: str = "Hello"):
        return f"Test Skill: {message}"
    
    manager.register_skill(
        name="test",
        handler=test_skill,
        description="测试 Skill",
        params_schema={
            "message": {"type": "string", "required": False, "default": "Hello"}
        }
    )
    
    # 调用 Skill
    result = invoke_skill("test", message="World")
    print(f"结果: {result}")
    
    # 列出所有 Skills
    print("\n已注册的 Skills:")
    for name, skill in manager.list_skills().items():
        print(f"  - {name}: {skill.description} (enabled: {skill.enabled})")
