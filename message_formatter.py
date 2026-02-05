#!/usr/bin/env python3
"""
消息格式化工具 - 优化飞书机器人的回复可读性
提供多种格式化选项来改善用户体验
"""

import re
from typing import Dict, List, Optional

class MessageFormatter:
    """消息格式化器"""
    
    # 无效提及模式
    INVALID_MENTION_PATTERNS = [
        r'@_user_\d+',  # 飞书无效用户提及
        r'@null',       # 空提及
        r'@undefined',  # 未定义提及
    ]
    
    # 内容类型识别
    CONTENT_TYPES = {
        'list_format': ['|', '----'],
        'heading_format': ['# ', '## ', '### '],
        'technical_content': ['系统', '管理', '流程', '操作', '业务'],
        'simple_content': ['你好', '谢谢', '再见', '帮助']
    }
    
    @staticmethod
    def preprocess_message(text: str) -> str:
        """预处理消息，移除无效提及等干扰内容"""
        if not text:
            return text
            
        import re
        
        # 移除无效提及
        for pattern in MessageFormatter.INVALID_MENTION_PATTERNS:
            text = re.sub(pattern, '', text)
        
        # 清理多余的空格
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @staticmethod
    def detect_content_type(text: str) -> str:
        """检测内容类型以选择合适的格式化策略"""
        if any(indicator in text for indicator in MessageFormatter.CONTENT_TYPES['list_format']):
            return 'technical_detailed'
        elif any(indicator in text for indicator in MessageFormatter.CONTENT_TYPES['heading_format']):
            return 'structured_info'
        elif any(indicator in text for indicator in MessageFormatter.CONTENT_TYPES['technical_content']):
            return 'technical_brief'
        elif any(indicator in text for indicator in MessageFormatter.CONTENT_TYPES['simple_content']):
            return 'simple'
        else:
            return 'general'
    
    @staticmethod
    def optimize_readability(text: str, content_type: str = None) -> str:
        """
        优化文本可读性
        主要改进：
        1. 将表格格式转换为更易读的列表格式
        2. 添加适当的分段和间距
        3. 优化标题层级
        4. 突出关键信息
        """
        if not text:
            return text
            
        # 自动检测内容类型
        if content_type is None:
            content_type = MessageFormatter.detect_content_type(text)
            
        # 保存原始文本用于对比
        original_text = text
        
        # 根据内容类型选择不同的处理策略
        if content_type == 'technical_detailed':
            text = MessageFormatter._process_technical_detailed(text)
        elif content_type == 'structured_info':
            text = MessageFormatter._process_structured_info(text)
        elif content_type == 'technical_brief':
            text = MessageFormatter._process_technical_brief(text)
        else:
            # 通用处理 - 即使是简单文本也会进行基础优化
            text = MessageFormatter._basic_formatting(text)
            text = MessageFormatter._optimize_headings(text)
            text = MessageFormatter._add_paragraph_spacing(text)
            text = MessageFormatter._highlight_key_info(text)
            text = MessageFormatter._clean_extra_whitespace(text)
        
        return text
    
    @staticmethod
    def _basic_formatting(text: str) -> str:
        """基础格式化 - 为所有文本提供最小优化"""
        lines = text.split('\n')
        result_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped:
                # 为短句添加轻微的格式化
                if len(stripped) < 50 and not any(char in stripped for char in ['#', '|', '-', '*']):
                    # 简单的问候语或短句优化
                    if any(word in stripped.lower() for word in ['你好', 'hello', 'hi', '您好', '测试']):
                        result_lines.append(f"👋 {stripped}")
                    else:
                        result_lines.append(stripped)
                else:
                    result_lines.append(stripped)
            else:
                result_lines.append("")
        
        return '\n'.join(result_lines)
    @staticmethod
    def _process_technical_detailed(text: str) -> str:
        """处理详细技术内容"""
        # 专门针对技术文档的优化
        text = MessageFormatter._convert_tables_to_readable_lists(text)
        text = MessageFormatter._optimize_technical_headings(text)
        text = MessageFormatter._add_technical_spacing(text)
        text = MessageFormatter._enhance_technical_formatting(text)
        return MessageFormatter._clean_extra_whitespace(text)
    
    @staticmethod
    def _process_structured_info(text: str) -> str:
        """处理结构化信息"""
        text = MessageFormatter._optimize_headings(text)
        text = MessageFormatter._add_paragraph_spacing(text)
        text = MessageFormatter._highlight_key_info(text)
        return MessageFormatter._clean_extra_whitespace(text)
    
    @staticmethod
    def _process_technical_brief(text: str) -> str:
        """处理简要技术内容"""
        text = MessageFormatter._simplify_technical_terms(text)
        text = MessageFormatter._optimize_headings(text)
        text = MessageFormatter._add_paragraph_spacing(text)
        return MessageFormatter._clean_extra_whitespace(text)
        """将表格格式转换为列表格式"""
        lines = text.split('\n')
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 检测表格头部（包含多个|分隔符的行）
            if '|' in line and line.count('|') >= 2:
                # 收集连续的表格行
                table_lines = []
                j = i
                
                # 向前查找表格结束
                while j < len(lines) and ('|' in lines[j] or lines[j].strip() == '' or 
                                        lines[j].startswith('-') or lines[j].startswith('----')):
                    if '|' in lines[j] and lines[j].strip() != '':
                        table_lines.append(lines[j].strip())
                    j += 1
                
                if len(table_lines) > 1:
                    # 转换表格为列表
                    converted = MessageFormatter._table_to_list(table_lines)
                    result_lines.extend(converted)
                    i = j  # 跳过已处理的表格行
                    continue
            
            result_lines.append(line)
            i += 1
        
        return '\n'.join(result_lines)
    
    @staticmethod
    def _convert_tables_to_readable_lists(text: str) -> str:
        """将表格格式转换为列表格式"""
        lines = text.split('\n')
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 检测表格头部（包含多个|分隔符的行）
            if '|' in line and line.count('|') >= 2:
                # 收集连续的表格行
                table_lines = []
                j = i
                
                # 向前查找表格结束
                while j < len(lines) and ('|' in lines[j] or lines[j].strip() == '' or 
                                        lines[j].startswith('-') or lines[j].startswith('----')):
                    if '|' in lines[j] and lines[j].strip() != '':
                        table_lines.append(lines[j].strip())
                    j += 1
                
                if len(table_lines) > 1:
                    # 转换表格为列表
                    converted = MessageFormatter._table_to_list(table_lines)
                    result_lines.extend(converted)
                    i = j  # 跳过已处理的表格行
                    continue
            
            result_lines.append(line)
            i += 1
        
        return '\n'.join(result_lines)
    
    @staticmethod
    def _table_to_list(table_lines: List[str]) -> List[str]:
        """将表格行转换为列表格式"""
        if len(table_lines) < 2:
            return table_lines
            
        result = []
        
        # 第一行通常是标题
        header = table_lines[0]
        cells = [cell.strip() for cell in header.split('|') if cell.strip()]
        
        if len(cells) >= 2:
            # 添加分类标题
            category_title = cells[0] if len(cells) > 0 else "项目"
            description_title = cells[1] if len(cells) > 1 else "说明"
            
            result.append(f"\n📌 {category_title} | {description_title}")
            result.append("─" * 30)
            
            # 处理数据行
            for line in table_lines[1:]:
                if '|' in line and not line.startswith('----'):
                    parts = [part.strip() for part in line.split('|') if part.strip() and not part.strip().startswith('----')]
                    if len(parts) >= 2:
                        item = parts[0]
                        desc = parts[1]
                        # 移除markdown粗体标记以便重新格式化
                        item_clean = item.replace('**', '').replace('*', '')
                        # 只保留第一个描述部分，忽略典型场景等额外信息
                        desc_main = desc.split('|')[0].strip()
                        # 清理描述中的多余格式
                        desc_clean = desc_main.replace('**', '').replace('*', '')
                        result.append(f"🔹 **{item_clean}** - {desc_clean}")
        
        return result
    
    @staticmethod
    def _optimize_headings(text: str) -> str:
        """优化标题层级和格式"""
        lines = text.split('\n')
        result_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # 处理不同级别的标题
            if stripped.startswith('###'):
                # 三级标题 - 主要分类
                title = stripped[3:].strip()
                result_lines.append(f"\n🎯 {title}")
                result_lines.append("═" * (len(title) + 2))
            elif stripped.startswith('##'):
                # 二级标题 - 大分类
                title = stripped[2:].strip()
                result_lines.append(f"\n🚀 {title}")
                result_lines.append("━" * (len(title) + 2))
            elif stripped.startswith('#'):
                # 一级标题 - 主标题
                title = stripped[1:].strip()
                result_lines.append(f"\n🌟 {title}")
                result_lines.append("━" * (len(title) + 2))
            else:
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    @staticmethod
    def _add_paragraph_spacing(text: str) -> str:
        """添加适当的段落间距"""
        lines = text.split('\n')
        result_lines = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # 在主要分类之间添加额外间距
            if stripped.startswith('🎯') or stripped.startswith('🚀') or stripped.startswith('🌟'):
                if i > 0 and result_lines and not result_lines[-1].strip() == '':
                    result_lines.append('')  # 在标题前添加空行
            
            # 在列表项之间保持适当间距
            if stripped.startswith('🔹') or stripped.startswith('🔸') or stripped.startswith('▫️'):
                # 如果前一行不是列表项，则添加空行
                if (i > 0 and lines[i-1].strip() and 
                    not lines[i-1].strip().startswith(('🔹', '🔸', '▫️', '-', '*', '•'))):
                    result_lines.append('')
            
            result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    @staticmethod
    def _highlight_key_info(text: str) -> str:
        """突出关键信息"""
        # 关键词高亮
        keywords = [
            r'(?:采购|生产|销售|调拨|委外|赠品|盘盈|其他)入库',
            r'(?:标准|无单|ASN预收货|越库)作业',
            r'(?:原材料|成品|半成品|商品|货物)',
            r'(?:订单|工单|质检|盘点|补货|退货)',
        ]
        
        for keyword_pattern in keywords:
            # 使用更温和的强调方式，避免过度格式化
            text = re.sub(keyword_pattern, r'**\g<0>**', text)
        
        return text
    
    @staticmethod
    def _clean_extra_whitespace(text: str) -> str:
        """清理多余的空白行"""
        lines = text.split('\n')
        result_lines = []
        empty_line_count = 0
        
        for line in lines:
            if line.strip() == '':
                empty_line_count += 1
                # 最多保留两个连续空行
                if empty_line_count <= 2:
                    result_lines.append(line)
            else:
                empty_line_count = 0
                result_lines.append(line)
        
        return '\n'.join(result_lines).strip()
    
    @staticmethod
    def _optimize_technical_headings(text: str) -> str:
        """优化技术文档标题"""
        lines = text.split('\n')
        result_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            if stripped.startswith('###'):
                title = stripped[3:].strip()
                result_lines.append(f"\n📘 {title}")
                result_lines.append("─" * min(len(title) + 2, 40))
            elif stripped.startswith('##'):
                title = stripped[2:].strip()
                result_lines.append(f"\n📚 {title}")
                result_lines.append("═" * min(len(title) + 2, 50))
            elif stripped.startswith('#'):
                title = stripped[1:].strip()
                result_lines.append(f"\n🎓 {title}")
                result_lines.append("═" * min(len(title) + 2, 60))
            else:
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    @staticmethod
    def _add_technical_spacing(text: str) -> str:
        """为技术内容添加适当间距"""
        lines = text.split('\n')
        result_lines = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # 在主要分类标题前后添加间距
            if stripped.startswith(('📘', '📚', '🎓')):
                if i > 0 and result_lines and not result_lines[-1].strip() == '':
                    result_lines.append('')
                
            # 在列表项之间添加适当间距
            if stripped.startswith('🔹'):
                if (i > 0 and lines[i-1].strip() and 
                    not lines[i-1].strip().startswith(('🔹', '🔸', '▫️', '-', '*', '•'))):
                    result_lines.append('')
            
            result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    @staticmethod
    def _enhance_technical_formatting(text: str) -> str:
        """增强技术内容格式化"""
        # 技术术语高亮
        tech_terms = [
            r'(?:采购|生产|销售|调拨|委外|赠品|盘盈|其他)入库',
            r'(?:标准|无单|ASN预收货|越库)作业?',
            r'(?:原材料|成品|半成品|商品|货物)',
            r'(?:订单|工单|质检|盘点|补货|退货)',
            r'(?:WMS|ERP|系统|流程|管理)',
        ]
        
        for term_pattern in tech_terms:
            text = re.sub(term_pattern, r'**\g<0>**', text)
        
        return text
    
    @staticmethod
    def _simplify_technical_terms(text: str) -> str:
        """简化技术术语表达"""
        # 将复杂的技术表述简化
        simplifications = {
            r'仓储管理\(WMS\)': '仓储管理',
            r'企业资源规划\(ERP\)': '企业管理系统',
            r'供应链管理\(SCM\)': '供应链管理',
            r'生产执行系统\(MES\)': '生产管理系统',
        }
        
        for pattern, replacement in simplifications.items():
            text = re.sub(pattern, replacement, text)
        
        return text
    
    @staticmethod
    def format_for_mobile(text: str) -> str:
        """
        为移动端优化格式
        特点：更简洁、更适合小屏幕阅读
        """
        # 使用更紧凑的格式
        text = text.replace('🔹', '•')
        text = text.replace('🔸', '◦')
        text = text.replace('▫️', '▪')
        
        # 缩短长行
        lines = text.split('\n')
        result_lines = []
        
        for line in lines:
            if len(line) > 80:  # 对于长行进行软换行
                # 简单的单词边界换行
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line + word) > 75:
                        if current_line:
                            result_lines.append(current_line)
                            current_line = word
                        else:
                            result_lines.append(word[:75] + "...")
                            current_line = word[75:] if len(word) > 75 else ""
                    else:
                        current_line = current_line + " " + word if current_line else word
                if current_line:
                    result_lines.append(current_line)
            else:
                result_lines.append(line)
        
        return '\n'.join(result_lines)

# 使用示例和测试
if __name__ == "__main__":
    # 测试原始文本（来自截图）
    test_text = """您好！您提到的"入库执行"和"入库方式"，通常出现在**仓储管理（WMS）**、**ERP系统**或**供应链管理系统**中。

### 一、按业务来源分类
入库存方式 | 说明 | 典型场景
----|----|----
**采购入库** | 供应商送货后，依据采购订单（PO）收货入库 | 原材料、成品采购
**生产入库** | 生产完工后，将产成品/半成品转入仓库 | 车间完工报工后入库
**销售退货入库** | 客户退回商品，经质检后重新入库 | 电商/零售退货处理
**调拨入库** | 从其他仓库/门店调入货物 | 分仓补货、区域调拨
**委外加工入库** | 委外加工完成后，加工方返回成品/半成品 | 外协加工回厂
**赠品/样品入库** | 非销售性质的物品（如促销赠品、样品）入库 | 市场活动支持
**盘盈入库** | 盘点发现实际库存多于账面，进行账务调整入库 | 库存盘点差异处理
**其他入库** | 不属于上述类别的零星入库（需手工录入原因） | 维修件、报废回收再利用等

### 二、按操作流程/技术实现分类
类型 | 说明
----|----
**标准入库** | 有对应上游单据（如采购订单、生产工单），系统自动带出信息
**无单入库** | 无前置单据，直接手工创建入库单（常用于紧急补货或临时收货）
**ASN预收货入库** | 供应商提前发送ASN（Advance Shipping Notice），仓库按预约计划收货
**越库作业** | 货物不入库，直接分拣转运（严格说不算"入库"，但常与入库流程并列）"""
    
    formatter = MessageFormatter()
    optimized = formatter.optimize_readability(test_text)
    
    print("原始文本:")
    print("-" * 50)
    print(test_text)
    print("\n" + "="*60 + "\n")
    print("优化后文本:")
    print("-" * 50)
    print(optimized)