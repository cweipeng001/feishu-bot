# Feishu Document Search Skill

飞书云文档智能检索技能 - 通过真实 API 调用搜索飞书知识库文档

## 功能描述

此技能用于在飞书知识库中搜索相关文档，支持：
- 🔍 智能关键词检索
- 📚 多文档结果返回
- 🔗 直接文档链接访问
- ⚡ 真实 OpenAPI MCP 调用

## 使用场景

当用户询问与飞书文档相关的问题时，自动触发此技能：
- "搜索XXX相关的文档"
- "查找XXX的资料"
- "帮我找XXX的说明文档"
- "XXX的文档在哪里"

## 前置条件

1. ✅ 飞书 OAuth 授权已完成
2. ✅ 用户已授权 `search:docs:read` 权限
3. ✅ OpenAPI MCP 服务已配置
4. ✅ App ID 和 App Secret 已设置

## 调用方式

### 方法 1: 直接调用 Python 函数

```python
from feishu_docs_openapi import search_feishu_knowledge

# 搜索文档
result = search_feishu_knowledge(query="测试", count=3)
print(result)
```

### 方法 2: 通过 Flask API

```bash
curl -X POST http://localhost:5004/test/doc-search \
  -H "Content-Type: application/json" \
  -d '{"query": "测试", "count": 3}'
```

### 方法 3: 在消息处理中自动触发

当用户消息包含触发关键词时，自动搜索并增强消息：
- 触发关键词：文档、知识库、wiki、查一下、搜索、找一下、帮我查、资料、教程、说明、手册

## 输入参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | ✅ | - | 搜索关键词 |
| `count` | integer | ❌ | 3 | 返回文档数量 |

## 输出格式

### 成功返回

```markdown
📚 **检索到的飞书文档内容：**

---
### 📄 文档 1: [文档标题]
- 链接: [文档URL]

**内容:**
文档类型: docx

---
### 📄 文档 2: [文档标题]
- 链接: [文档URL]

**内容:**
文档类型: sheet

---
以上是检索到的文档内容，请基于这些信息回答用户问题。
```

### 失败返回

```
未找到相关文档。
```

## 技术实现

### 1. 核心模块

- **feishu_docs_openapi.py** - OpenAPI 文档检索主模块
- **real_openapi_client.py** - 真实 API 客户端实现
- **simple_openapi_client.py** - 简单客户端（备用）

### 2. API 调用流程

```
用户查询 → 关键词提取 → OpenAPI MCP 初始化 → 
调用 docx_builtin_search → 解析结果 → 格式化输出
```

### 3. 关键代码

#### 搜索文档
```python
def search_feishu_knowledge(query: str, count: int = 3) -> str:
    """搜索飞书知识库"""
    if HAS_REAL_CLIENT:
        return search_feishu_knowledge_real(query, count)
    else:
        return search_feishu_knowledge_simple(query, count)
```

#### 真实 API 调用
```python
def search_documents(self, query: str, count: int = 3) -> List[DocumentContent]:
    """使用 docx_builtin_search 搜索文档"""
    result = self.call_tool("docx_builtin_search", {
        "data": {
            "search_key": query,
            "count": count
        },
        "useUAT": True  # 关键：使用用户访问令牌
    })
    # 解析结果...
```

## 配置说明

### 环境变量

```bash
# 飞书应用凭证
FEISHU_APP_ID=cli_a9fdafec72fbdcc4
FEISHU_APP_SECRET=rVD7FQHwy6flSygRjkCHiPsq1HgZgCIg

# 文档搜索配置
FEISHU_DOC_SEARCH_ENABLED=true
FEISHU_DOC_AUTO_DETECT=true
FEISHU_DOC_MAX_RESULTS=3
```

### 触发关键词配置

在 `feishu_bot.py` 中配置：

```python
DOC_SEARCH_CONFIG = {
    "enabled": True,
    "auto_detect": True,
    "max_docs": 3,
    "trigger_keywords": [
        "文档", "知识库", "wiki", "查一下", 
        "搜索", "找一下", "帮我查", "资料", 
        "教程", "说明", "手册"
    ]
}
```

## 错误处理

### 常见错误及解决方案

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| 未授权 | 用户未完成 OAuth 授权 | 访问 `/auth/feishu` 完成授权 |
| 找到 0 个文档 | 搜索关键词不匹配 | 优化搜索关键词 |
| MCP 初始化失败 | OpenAPI MCP 服务异常 | 检查 App ID/Secret 配置 |
| useUAT 参数缺失 | 未设置用户令牌 | 确保 useUAT: true |

## 性能优化

1. **进程复用** - OpenAPI MCP 进程自动管理，避免重复启动
2. **结果缓存** - 可选：缓存搜索结果，减少 API 调用
3. **异步处理** - 文档搜索在后台线程执行，不阻塞消息处理
4. **智能降级** - 当 AI 服务不可用时，仍返回文档搜索结果

## 使用示例

### 示例 1: 基础搜索

**用户输入:**
```
搜索关于测试的文档
```

**系统处理:**
1. 检测到关键词"搜索"、"文档"
2. 提取查询："测试"
3. 调用 OpenAPI 搜索
4. 返回 3 个相关文档

**返回结果:**
```
📚 已为您搜索到相关飞书文档：

---
📄 文档 1: 测试方案
- 链接: https://k7ftx11633c.feishu.cn/docx/doxcnUd0FW7tCwogVi4nz7V2oRg

⚠️ 注意：AI智能体服务当前不可用，仅返回文档搜索结果。
请点击文档链接查看完整内容，或稍后再试。
```

### 示例 2: 集成到对话流程

**用户输入:**
```
数码模的测试流程是什么？
```

**系统处理:**
1. 自动检测需要文档支持
2. 搜索"数码模 测试流程"
3. 将文档内容注入 LLM 上下文
4. 生成基于文档的回答

## 扩展功能

### 未来可添加的功能

1. **高级搜索**
   - 支持文档类型过滤（docx/sheet/wiki）
   - 支持时间范围筛选
   - 支持作者筛选

2. **智能推荐**
   - 基于用户历史搜索推荐相关文档
   - 热门文档推荐

3. **文档预览**
   - 获取文档摘要
   - 显示文档前几段内容

4. **权限管理**
   - 检查用户文档访问权限
   - 过滤无权限文档

## 测试验证

### 单元测试

```bash
# 测试文档搜索功能
python3 feishu_docs_openapi.py
```

### 集成测试

```bash
# 模拟飞书回调
curl -X POST http://localhost:5004/feishu/callback \
  -H "Content-Type: application/json" \
  -d '{
    "header": {
      "event_type": "im.message.receive_v1",
      "token": "YOUR_TOKEN"
    },
    "event": {
      "message": {
        "content": "{\"text\":\"搜索测试文档\"}"
      }
    }
  }'
```

### 端到端测试

1. 在飞书中发送消息："搜索测试文档"
2. 验证机器人是否返回文档搜索结果
3. 验证文档链接是否可访问

## 注意事项

⚠️ **重要提示**

1. **不使用 docx_builtin_import** - 仅使用搜索 API，不导入文档
2. **必须设置 useUAT: true** - 使用用户访问令牌
3. **需要用户授权** - 用户必须完成 OAuth 授权流程
4. **API 限流** - 注意飞书 API 调用频率限制

## 维护日志

- 2026-02-05: 创建初始版本，支持基础文档搜索
- 2026-02-05: 添加降级模式支持，AI 不可用时仍返回文档
- 2026-02-05: 优化关键词提取逻辑
- 2026-02-05: 完善端到端测试验证

## 相关文档

- [飞书 OpenAPI 文档](https://open.feishu.cn/document/)
- [OpenAPI MCP 集成指南](https://github.com/larksuite/lark-mcp)
- [OAuth 授权流程](https://open.feishu.cn/document/common-capabilities/sso/api/overview)

## 支持与反馈

如有问题或建议，请联系开发团队。
