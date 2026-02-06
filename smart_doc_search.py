#!/usr/bin/env python3
"""
智能文档搜索模块
基于自然语言分析自动判断是否需要调用文档搜索功能
"""

import re
import logging
from typing import List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SearchAnalysis:
    """搜索分析结果"""
    should_search: bool
    confidence: float  # 置信度 0-1
    reason: str
    extracted_query: str

class SmartDocSearchAnalyzer:
    """智能文档搜索分析器"""
    
    def __init__(self):
        # 扩展的触发关键词
        self.trigger_keywords = [
            # 基础关键词
            "文档", "知识库", "wiki", "查一下", "搜索", "找一下", "帮我查", 
            "资料", "教程", "说明", "手册", "查找", "查询", "检索", "看看", 
            "翻阅", "浏览", "参考资料", "相关资料", "文档资料",
            
            # 文档类型
            "项目文档", "技术文档", "产品文档", "需求文档", "设计文档", 
            "开发文档", "测试文档", "运维文档", "用户手册", "操作手册",
            
            # 内容类型
            "流程", "规范", "标准", "指南", "最佳实践", "制度", "规定"
        ]
        
        # 疑问词
        self.question_indicators = [
            "怎么", "如何", "怎样", "什么", "哪个", "哪些",
            "有没有", "是否存在", "能否", "可以", "应该",
            "请教", "请问", "求助", "帮忙", "求"
        ]
        
        # 内容相关词
        self.content_words = [
            "流程", "步骤", "方法", "方式", "操作", "配置", 
            "设置", "安装", "部署", "使用", "规范", "标准", 
            "要求", "规定", "文档", "资料", "信息"
        ]
        
        # 上下文指示词
        self.context_indicators = [
            "项目", "产品", "系统", "平台", "工具", "服务",
            "sdk", "api", "接口", "框架", "组件", "模块"
        ]
        
        # 需求动词
        self.need_verbs = [
            "了解", "熟悉", "掌握", "学习", "研究", "查看",
            "需要", "准备", "整理", "参考", "查阅"
        ]
        
        # 问候语（用于排除）
        self.greetings = [
            "你好", "您好", "hello", "hi", "早上好", "下午好",
            "晚上好", "辛苦了", "谢谢", "感谢"
        ]
    
    def analyze(self, user_text: str) -> SearchAnalysis:
        """
        分析用户消息，判断是否需要文档搜索
        
        Args:
            user_text: 用户消息文本
            
        Returns:
            SearchAnalysis: 分析结果
        """
        text_lower = user_text.lower().strip()
        
        # 1. 基础检查
        if not text_lower:
            return SearchAnalysis(False, 0.0, "空消息", "")
        
        # 2. 关键词匹配（高权重）
        keyword_match = self._check_keywords(text_lower)
        if keyword_match:
            query = self._extract_query(text_lower)
            return SearchAnalysis(True, 0.9, f"匹配关键词: {keyword_match}", query)
        
        # 3. 疑问句模式（中高权重）
        question_match = self._check_question_patterns(text_lower)
        if question_match:
            query = self._extract_query(text_lower)
            return SearchAnalysis(True, 0.8, f"疑问句模式: {question_match}", query)
        
        # 4. 任务导向语句（中权重）
        task_match = self._check_task_patterns(text_lower)
        if task_match:
            query = self._extract_query(text_lower)
            return SearchAnalysis(True, 0.7, f"任务导向: {task_match}", query)
        
        # 5. 上下文相关性（中权重）
        context_match = self._check_context_patterns(text_lower)
        if context_match:
            query = self._extract_query(text_lower)
            return SearchAnalysis(True, 0.6, f"上下文相关: {context_match}", query)
        
        # 6. 复杂查询判断（低权重）
        if self._is_complex_query(text_lower):
            query = self._extract_query(text_lower)
            return SearchAnalysis(True, 0.5, "复杂查询需要文档支持", query)
        
        # 7. 不需要搜索
        return SearchAnalysis(False, 0.1, "常规对话，无需文档搜索", "")
    
    def _check_keywords(self, text: str) -> str:
        """检查关键词匹配"""
        for keyword in self.trigger_keywords:
            if keyword.lower() in text:
                return keyword
        return ""
    
    def _check_question_patterns(self, text: str) -> str:
        """检查疑问句模式"""
        # 疑问词 + 内容词组合
        for indicator in self.question_indicators:
            if indicator in text:
                for content_word in self.content_words:
                    if content_word in text:
                        return f"{indicator}{content_word}"
        
        # 正则表达式模式
        patterns = [
            r"怎么.{0,15}(做|用|操作|配置|设置|部署)",
            r"如何.{0,15}(做|用|操作|配置|设置|部署)",
            r"(什么是|什么是|什么叫).{1,20}",
            r".{1,20}(在哪|怎么找|哪里有)",
            r"(有没有|是否存在).{1,20}(文档|说明|教程|资料)",
            r"(请教|请问|求助).{1,20}(如何|怎么)"
        ]
        
        for pattern in patterns:
            if re.search(pattern, text):
                return "疑问句模式匹配"
        
        return ""
    
    def _check_task_patterns(self, text: str) -> str:
        """检查任务导向语句"""
        patterns = [
            r"(需要|准备|整理).{0,15}(文档|资料|信息)",
            r"(了解|学习|研究).{0,15}(流程|规范|标准|操作)",
            r"(参考|查阅).{0,15}(文档|资料)",
            r"(查找|搜索).{0,15}(相关|有关).{0,10}(资料|信息)"
        ]
        
        for pattern in patterns:
            if re.search(pattern, text):
                return "任务导向语句匹配"
        
        return ""
    
    def _check_context_patterns(self, text: str) -> str:
        """检查上下文相关性"""
        for indicator in self.context_indicators:
            if indicator in text:
                for verb in self.need_verbs:
                    if verb in text:
                        return f"{verb}{indicator}"
        return ""
    
    def _is_complex_query(self, text: str) -> bool:
        """判断是否为复杂查询"""
        # 长度判断
        if len(text) < 10:
            return False
            
        # 排除问候语
        if any(greeting in text for greeting in self.greetings):
            return False
            
        # 结尾不是简单标点
        if text.endswith(('?', '？', '.', '。', '!', '！')):
            # 但是疑问句可能是需要搜索的
            question_endings = [('?', '？')]
            if any(ending in text for ending in ['?', '？']):
                return True
        
        # 包含具体内容词汇
        content_indicators = ["流程", "步骤", "方法", "配置", "使用", "操作"]
        if any(indicator in text for indicator in content_indicators):
            return True
            
        return False
    
    def _extract_query(self, text: str) -> str:
        """从文本中提取搜索关键词"""
        # 移除常见的前置词
        prefixes = ["帮我", "请", "想", "要", "查找", "搜索", "查一下", "找一下"]
        query_text = text.lower()
        
        for prefix in prefixes:
            if query_text.startswith(prefix):
                query_text = query_text[len(prefix):].strip()
                break
        
        # 移除后缀词
        suffixes = ["的文档", "的资料", "怎么做", "如何做", "相关信息"]
        for suffix in suffixes:
            if query_text.endswith(suffix):
                query_text = query_text[:-len(suffix)].strip()
                break
        
        # 清理特殊字符
        query_text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', query_text)
        
        return query_text.strip() if query_text else text.strip()

# 全局实例
_analyzer = SmartDocSearchAnalyzer()

def should_search_documents_smart(user_text: str) -> Tuple[bool, float, str, str]:
    """
    智能判断是否需要文档搜索
    
    Args:
        user_text: 用户消息文本
        
    Returns:
        Tuple[bool, float, str, str]: (是否搜索, 置信度, 原因, 提取的查询词)
    """
    analysis = _analyzer.analyze(user_text)
    return analysis.should_search, analysis.confidence, analysis.reason, analysis.extracted_query

def get_search_confidence(user_text: str) -> float:
    """获取搜索置信度"""
    _, confidence, _, _ = should_search_documents_smart(user_text)
    return confidence

# 测试函数
def test_smart_analyzer():
    """测试智能分析器"""
    test_cases = [
        "帮我查一下入库流程的文档",
        "怎么配置这个系统的API接口？",
        "项目的技术规范在哪里可以找到？",
        "有没有关于用户认证的说明文档？",
        "你好，今天天气怎么样？",
        "请教一下数据库设计的最佳实践",
        "需要准备一份产品需求文档",
        "了解微服务架构的设计模式",
        "简单介绍一下你们公司",
        "查找最近的项目进度报告"
    ]
    
    print("🤖 智能文档搜索分析测试")
    print("=" * 50)
    
    for text in test_cases:
        should_search, confidence, reason, query = should_search_documents_smart(text)
        status = "🔍 需要搜索" if should_search else "📝 无需搜索"
        print(f"{status} (置信度: {confidence:.1f}) [{reason}]")
        print(f"  输入: {text}")
        if should_search:
            print(f"  查询词: {query}")
        print()

if __name__ == "__main__":
    test_smart_analyzer()