#!/usr/bin/env python3
"""
真实的飞书 OpenAPI 文档检索客户端
通过标准输入输出与 OpenAPI MCP 进程通信
"""

import os
import json
import logging
import subprocess
import threading
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DocumentContent:
    """文档内容"""
    title: str
    content: str
    url: str
    truncated: bool = False

class RealFeishuOpenAPIClient:
    """真实的飞书 OpenAPI 客户端"""
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self._lock = threading.Lock()
        
    def start_mcp_process(self) -> bool:
        """启动 OpenAPI MCP 进程"""
        with self._lock:
            if self.process and self.process.poll() is None:
                logger.info("✅ OpenAPI MCP 进程已在运行")
                return True
            
            try:
                logger.info("🚀 启动 OpenAPI MCP 进程...")
                
                # 构建命令
                cmd = [
                    "npx", "-y", "@larksuiteoapi/lark-mcp",
                    "mcp",
                    "-a", self.app_id,
                    "-s", self.app_secret,
                    "--oauth"
                ]
                
                # 启动进程，使用管道进行通信
                self.process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                logger.info("✅ OpenAPI MCP 进程启动成功")
                return True
                
            except Exception as e:
                logger.error(f"❌ 启动 OpenAPI MCP 进程失败: {e}")
                return False
    
    def stop_mcp_process(self):
        """停止 OpenAPI MCP 进程"""
        with self._lock:
            if self.process:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=5)
                    logger.info("⏹️ OpenAPI MCP 进程已停止")
                except:
                    self.process.kill()
                finally:
                    self.process = None
    
    def _get_next_id(self) -> int:
        """获取下一个请求 ID"""
        self.request_id += 1
        return self.request_id
    
    def _send_request(self, method: str, params: Dict = None) -> Optional[Dict]:
        """
        发送 JSON-RPC 请求到 MCP 进程
        
        Args:
            method: 方法名
            params: 参数
            
        Returns:
            响应字典
        """
        if not self.start_mcp_process():
            return None
        
        try:
            # 构造 JSON-RPC 请求
            request = {
                "jsonrpc": "2.0",
                "id": self._get_next_id(),
                "method": method
            }
            
            if params:
                request["params"] = params
            
            logger.info(f"📡 发送请求: {method}")
            logger.debug(f"请求内容: {json.dumps(request, ensure_ascii=False)}")
            
            # 发送请求
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json)
            self.process.stdin.flush()
            
            # 读取响应
            response_line = self.process.stdout.readline()
            if response_line:
                response = json.loads(response_line.strip())
                logger.debug(f"响应内容: {json.dumps(response, ensure_ascii=False)}")
                
                if "error" in response:
                    logger.error(f"❌ MCP 错误: {response['error']}")
                    return None
                
                return response.get("result")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 发送请求失败: {e}")
            return None
    
    def initialize(self) -> bool:
        """初始化 MCP 连接"""
        result = self._send_request("initialize", {
            "protocolVersion": "2024-01-01",
            "capabilities": {},
            "clientInfo": {
                "name": "feishu-bot-client",
                "version": "1.0.0"
            }
        })
        if result:
            logger.info(f"✅ MCP 初始化成功: {result}")
            return True
        
        # 读取 stderr 获取详细错误信息
        if self.process and self.process.stderr:
            try:
                import select
                # 非阻塞读取 stderr
                if hasattr(select, 'select'):
                    ready, _, _ = select.select([self.process.stderr], [], [], 0.1)
                    if ready:
                        error_output = self.process.stderr.read()
                        if error_output:
                            logger.error(f"❌ MCP 进程错误输出: {error_output}")
            except Exception as e:
                logger.warning(f"无法读取 stderr: {e}")
        
        logger.error("❌ MCP 初始化失败")
        return False
    
    def list_tools(self) -> Optional[List[Dict]]:
        """列出可用工具"""
        result = self._send_request("tools/list")
        if result and "tools" in result:
            tools = result["tools"]
            logger.info(f"🔧 可用工具数量: {len(tools)}")
            for tool in tools:
                logger.info(f"  - {tool.get('name', 'Unknown')}: {tool.get('description', '')[:50]}...")
            return tools
        return None
    
    def call_tool(self, tool_name: str, arguments: Dict) -> Optional[Any]:
        """
        调用具体工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        result = self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        
        if result:
            logger.info(f"✅ 工具 {tool_name} 调用成功")
            return result
        return None
    
    def search_documents(self, query: str, count: int = 3) -> List[DocumentContent]:
        """
        搜索文档（使用 docx_builtin_search）
        """
        try:
            logger.info(f"🔍 搜索文档: '{query}'")
            
            # 初始化连接
            if not self.initialize():
                logger.error("❌ MCP 初始化失败")
                return []
            
            # 调用 docx_builtin_search
            result = self.call_tool("docx_builtin_search", {
                "data": {
                    "search_key": query,
                    "count": count
                },
                "useUAT": True
            })
            
            if result:
                # 解析搜索结果
                content_list = result.get("content", [])
                if content_list:
                    text_content = content_list[0].get("text", "")
                    try:
                        search_result = json.loads(text_content)
                        documents = []
                        docs_entities = search_result.get("docs_entities", [])
                        
                        for doc in docs_entities[:count]:
                            documents.append(DocumentContent(
                                title=doc.get("title", "未知标题"),
                                content=f"文档类型: {doc.get('docs_type', 'unknown')}",
                                url=f"https://k7ftx11633c.feishu.cn/{doc.get('docs_type', 'docx')}/{doc.get('docs_token', '')}",
                                truncated=False
                            ))
                        
                        logger.info(f"✅ 找到 {len(documents)} 个文档")
                        return documents
                    except json.JSONDecodeError:
                        logger.error("❌ JSON 解析失败")
            
            # 如果没有结果，返回空列表
            logger.info("ℹ️ 未找到相关文档")
            return []
            
        except Exception as e:
            logger.error(f"❌ 文档搜索失败: {e}")
            return []
    
    def get_document_content(self, document_id: str, doc_type: str = "docx") -> Optional[DocumentContent]:
        """
        获取文档内容（仅返回基础信息，不支持完整内容获取）
        
        注意：飞书 OpenAPI MCP 当前不支持直接获取文档完整内容，
        只能通过搜索结果获取文档的基础信息和链接。
        用户可以点击链接在飞书中查看完整内容。
        """
        try:
            logger.info(f"📄 获取文档信息: {document_id}")
            
            return DocumentContent(
                title=f"文档: {document_id}",
                content=f"文档类型: {doc_type}\n\n⚠️ 暂不支持直接获取完整文档内容。\n请点击链接在飞书中查看完整内容。",
                url=f"https://k7ftx11633c.feishu.cn/{doc_type}/{document_id}",
                truncated=False
            )
            
        except Exception as e:
            logger.error(f"❌ 获取文档信息失败: {e}")
            return None

def get_real_openapi_client() -> RealFeishuOpenAPIClient:
    """获取真实的 OpenAPI 客户端"""
    load_dotenv()
    
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    
    if not app_id or not app_secret:
        raise ValueError("请在 .env 文件中配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
    
    return RealFeishuOpenAPIClient(app_id, app_secret)

def search_feishu_knowledge_real(query: str, count: int = 3) -> str:
    """
    真实的飞书知识库搜索
    """
    try:
        client = get_real_openapi_client()
        documents = client.search_documents(query, count)
        
        if not documents:
            return "未找到相关文档。"
        
        formatted_parts = ["📚 **检索到的飞书文档内容：**\n"]
        
        for i, doc in enumerate(documents, 1):
            truncate_hint = " (内容已截断)" if doc.truncated else ""
            
            part = f"""
---
### 📄 文档 {i}: {doc.title}
- 链接: {doc.url}
{truncate_hint}

**内容:**
{doc.content}
"""
            formatted_parts.append(part)
        
        formatted_parts.append("\n---\n以上是检索到的文档内容，请基于这些信息回答用户问题。")
        return "\n".join(formatted_parts)
        
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return f"❌ 搜索失败: {str(e)}"

# 程序退出时清理资源
import atexit
client_instance = None
def cleanup():
    global client_instance
    if client_instance:
        client_instance.stop_mcp_process()

atexit.register(cleanup)

if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("🧪 真实 OpenAPI 文档检索测试")
    print("=" * 60)
    
    try:
        result = search_feishu_knowledge_real("测试", 1)
        print(result)
    except Exception as e:
        print(f"测试失败: {e}")