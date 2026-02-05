#!/usr/bin/env python3
"""
飞书机器人回复格式化效果演示
展示优化前后的对比效果
"""

from message_formatter import MessageFormatter

def demonstrate_formatting():
    """演示格式化效果"""
    
    # 原始的密集表格格式（模拟AI返回的内容）
    original_text = """您好！您提到的"入库执行"和"入库方式"，通常出现在**仓储管理（WMS）**、**ERP系统**或**供应链管理系统**中。

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
**越库作业** | 货物不入库，直接分拣转运（严格说不算"入库"，但常与入库流程并列）

### 三、注意事项
1. 不同企业的入库流程可能有所差异
2. 具体操作需遵循企业内部规定
3. 建议结合实际业务场景灵活应用"""

    print("=" * 80)
    print("🤖 飞书机器人回复格式化优化演示")
    print("=" * 80)
    print()
    
    print("📋 原始回复格式（AI直接输出）:")
    print("-" * 50)
    print(original_text)
    print()
    
    print("=" * 80)
    print("✨ 优化后格式（提升可读性）:")
    print("-" * 50)
    
    # 应用格式化
    formatter = MessageFormatter()
    optimized_text = formatter.optimize_readability(original_text)
    
    print(optimized_text)
    print()
    
    print("=" * 80)
    print("📊 优化要点总结:")
    print("=" * 80)
    print("✅ 表格转换: 将密集的'|'分隔表格转换为清晰的列表格式")
    print("✅ 视觉层次: 使用图标和分隔线创建清晰的视觉层级")
    print("✅ 间距优化: 添加适当的空白行提高可读性")
    print("✅ 标题美化: 用emoji和装饰线美化各级标题")
    print("✅ 重点突出: 保留关键技术术语的强调格式")
    print("✅ 移动适配: 更适合手机端阅读的紧凑格式")
    print()
    
    # 显示字符统计对比
    original_chars = len(original_text)
    optimized_chars = len(optimized_text)
    print(f"📈 字符统计:")
    print(f"   原始格式: {original_chars} 字符")
    print(f"   优化格式: {optimized_chars} 字符")
    print(f"   增加幅度: {((optimized_chars - original_chars) / original_chars * 100):+.1f}%")

if __name__ == "__main__":
    demonstrate_formatting()