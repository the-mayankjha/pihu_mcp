import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pihu.llm.base import ToolDefinition
from pihu.config.settings import settings
from pihu.events.bus import bus
from pihu.events.types import AgentEvent, EventType

class MCPServerSession:
    """Encapsulates a connected MCP server stdio session."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.session: Optional[ClientSession] = None
        self._exit_stack = None

    async def connect(self) -> List[ToolDefinition]:
        command = self.config.get("command")
        args = self.config.get("args", [])
        env = self.config.get("env", os.environ.copy())

        # Expand ${PROJECT_ROOT} if present
        expanded_args = [
            arg.replace("${PROJECT_ROOT}", str(settings.project_root)) if isinstance(arg, str) else arg
            for arg in args
        ]

        server_params = StdioServerParameters(
            command=command,
            args=expanded_args,
            env=env
        )

        from contextlib import AsyncExitStack
        self._exit_stack = AsyncExitStack()
        try:
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            await self.session.initialize()
            tools_result = await self.session.list_tools()

            discovered_tools = []
            for t in tools_result.tools:
                discovered_tools.append(
                    ToolDefinition(
                        name=t.name,
                        description=t.description or f"MCP tool {t.name} from {self.name}",
                        parameters=t.inputSchema if isinstance(t.inputSchema, dict) else {}
                    )
                )

            return discovered_tools
        except Exception as e:
            await self.close()
            raise e

    async def close(self) -> None:
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except BaseException:
                pass
            self._exit_stack = None
            self.session = None

class MCPManager:
    """Manages MCP server discovery, connection lifecycles, and tool execution."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or settings.mcp_config_path
        self.sessions: Dict[str, MCPServerSession] = {}
        self.tool_map: Dict[str, Tuple[str, str]] = {}  # namespaced_name -> (server_name, original_tool_name)
        self.tools: List[ToolDefinition] = []

    async def load_and_initialize(self) -> List[ToolDefinition]:
        if not self.config_path.exists():
            await bus.emit(
                AgentEvent(
                    type=EventType.TOOL_DISCOVERED,
                    component="mcp_manager",
                    status="warning",
                    message=f"MCP configuration file not found at {self.config_path}",
                )
            )
            return []

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception as e:
            await bus.emit(
                AgentEvent(
                    type=EventType.ERROR,
                    component="mcp_manager",
                    status="error",
                    message=f"Failed to read MCP config: {str(e)}"
                )
            )
            return []

        servers_config = config_data.get("servers", {})
        self.tools.clear()
        self.tool_map.clear()

        for server_name, server_cfg in servers_config.items():
            try:
                session = MCPServerSession(server_name, server_cfg)
                tools = await session.connect()
                self.sessions[server_name] = session

                for t in tools:
                    self.tools.append(t)
                    self.tool_map[t.name] = (server_name, t.name)
                    self.tool_map[f"{server_name}__{t.name}"] = (server_name, t.name)

                await bus.emit(
                    AgentEvent(
                        type=EventType.TOOL_DISCOVERED,
                        component="mcp_manager",
                        status="success",
                        message=f"Discovered {len(tools)} tools from server '{server_name}'",
                        details={"server": server_name, "tools": [t.name for t in tools]}
                    )
                )
            except Exception as e:
                await bus.emit(
                    AgentEvent(
                        type=EventType.ERROR,
                        component="mcp_manager",
                        status="warning",
                        message=f"Failed to initialize MCP server '{server_name}': {str(e)}"
                    )
                )

        return self.tools

    async def execute_tool(self, namespaced_tool_name: str, arguments: Dict[str, Any]) -> str:
        if namespaced_tool_name not in self.tool_map:
            raise KeyError(f"Unknown MCP tool: {namespaced_tool_name}")

        server_name, original_tool_name = self.tool_map[namespaced_tool_name]
        server_session = self.sessions.get(server_name)

        if not server_session or not server_session.session:
            raise RuntimeError(f"MCP server session for '{server_name}' is not connected.")

        await bus.emit(
            AgentEvent(
                type=EventType.TOOL_STARTED,
                component="mcp_manager",
                status="running",
                message=f"Executing tool {namespaced_tool_name}",
                details={"tool": namespaced_tool_name, "arguments": arguments}
            )
        )

        try:
            result = await asyncio.wait_for(
                server_session.session.call_tool(original_tool_name, arguments),
                timeout=settings.mcp_tool_timeout
            )

            # Format tool result text
            result_texts = []
            if hasattr(result, "content") and result.content:
                for item in result.content:
                    if hasattr(item, "text"):
                        result_texts.append(item.text)
                    else:
                        result_texts.append(str(item))

            output_str = "\n".join(result_texts) if result_texts else "Tool executed successfully with no output."

            await bus.emit(
                AgentEvent(
                    type=EventType.TOOL_COMPLETED,
                    component="mcp_manager",
                    status="success",
                    message=f"Tool {namespaced_tool_name} completed successfully",
                    details={"tool": namespaced_tool_name, "output_preview": output_str[:150]}
                )
            )

            return output_str

        except Exception as e:
            error_msg = f"Tool execution error for {namespaced_tool_name}: {str(e)}"
            await bus.emit(
                AgentEvent(
                    type=EventType.ERROR,
                    component="mcp_manager",
                    status="error",
                    message=error_msg,
                    details={"tool": namespaced_tool_name, "error": str(e)}
                )
            )
            raise RuntimeError(error_msg) from e

    async def close_all(self) -> None:
        for name, session in list(self.sessions.items()):
            try:
                await session.close()
            except Exception:
                pass
        self.sessions.clear()
