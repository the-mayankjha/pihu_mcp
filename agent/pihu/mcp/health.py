"""
MCP Health Probe Runner & Tool Discovery Validator.
"""

import sys
import asyncio
from typing import Dict, Any, List, Tuple
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPHealthProbe:
    """Verifies server responsiveness and inspects available tools post-installation."""

    @staticmethod
    async def probe_stdio_server(command: str, args: List[str], env: Dict[str, str], timeout: float = 6.0) -> Tuple[bool, List[str], str]:
        """Pings a stdio MCP server, performs handshake, and returns (success, tool_list, message)."""
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )

        from contextlib import AsyncExitStack
        async with AsyncExitStack() as stack:
            try:
                devnull = open("/dev/null", "w") if sys.platform != "win32" else None
                read_stream, write_stream = await stack.enter_async_context(
                    stdio_client(server_params, errlog=devnull)
                )
                session = await stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )

                async def _handshake():
                    await session.initialize()
                    res = await session.list_tools()
                    return [t.name for t in res.tools]

                tools = await asyncio.wait_for(_handshake(), timeout=timeout)
                return True, tools, f"Healthy: Discovered {len(tools)} tools."
            except Exception as e:
                return False, [], f"Health check probe failed: {str(e)}"
