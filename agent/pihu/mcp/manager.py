import os
import sys
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

def resolve_mcp_servers_dir() -> Path:
    """Find the directory containing built-in MCP server scripts."""
    candidates = [
        Path(__file__).resolve().parent / "servers",
        Path(__file__).resolve().parent.parent.parent.parent / "mcp" / "servers",
        Path.cwd() / "src-tauri" / "pihu_mcps" / "mcp" / "servers",
        Path.cwd() / "mcp" / "servers",
    ]
    for c in candidates:
        if c.is_dir() and (c / "pihu_file_mcp.py").exists():
            return c
    return candidates[0]

def resolve_mcp_config_path(custom_path: Optional[Path] = None) -> Path:
    """Resolve the active MCP config.json path with intelligent fallback."""
    if custom_path and custom_path.exists():
        return custom_path

    env_cfg = os.getenv("PIHU_MCP_CONFIG_PATH")
    if env_cfg and Path(env_cfg).exists():
        return Path(env_cfg)

    local_cfg = Path.cwd() / "mcp" / "config.json"
    if local_cfg.exists():
        return local_cfg

    home_cfg = Path.home() / ".pihu" / "mcp_config.json"
    if home_cfg.exists():
        return home_cfg

    candidates = [
        Path(__file__).resolve().parent / "default_config.json",
        Path(__file__).resolve().parent.parent.parent.parent / "mcp" / "config.json",
        Path.cwd() / "src-tauri" / "pihu_mcps" / "mcp" / "config.json",
    ]
    for c in candidates:
        if c.exists():
            return c

    return Path(__file__).resolve().parent / "default_config.json"

class MCPServerSession:
    """Encapsulates a connected MCP server stdio session."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.session: Optional[ClientSession] = None
        self._exit_stack = None

    async def connect(self, timeout: float = 6.0) -> List[ToolDefinition]:
        command = self.config.get("command", "")
        args = self.config.get("args", [])
        env = self.config.get("env", os.environ.copy())

        servers_dir = str(resolve_mcp_servers_dir())
        project_root = str(settings.project_root)
        python_exec = sys.executable

        if command in ("${PYTHON_EXEC}", "python", "python3"):
            command = python_exec

        expanded_args = []
        for arg in args:
            if isinstance(arg, str):
                val = (
                    arg.replace("${SERVERS_DIR}", servers_dir)
                    .replace("${PROJECT_ROOT}", project_root)
                    .replace("${PYTHON_EXEC}", python_exec)
                )
                expanded_args.append(val)
            else:
                expanded_args.append(arg)

        server_params = StdioServerParameters(
            command=command,
            args=expanded_args,
            env=env
        )

        from contextlib import AsyncExitStack
        self._exit_stack = AsyncExitStack()

        async def _do_connect():
            devnull = open(os.devnull, "w")
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(server_params, errlog=devnull)
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

        try:
            return await asyncio.wait_for(_do_connect(), timeout=timeout)
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
        self.config_path = resolve_mcp_config_path(config_path)
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
                details={"tool": namespaced_tool_name, "server": server_name, "arguments": arguments}
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
                    details={
                        "tool": namespaced_tool_name,
                        "server": server_name,
                        "arguments": arguments,
                        "output_preview": output_str[:200]
                    }
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
        self.tools.clear()
        self.tool_map.clear()
