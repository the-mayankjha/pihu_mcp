"""Bounded MCP protocol checks with portable stderr handling."""
import asyncio
from contextlib import AsyncExitStack
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
class MCPHealthProbe:
    @staticmethod
    async def probe_stdio_server(command, args, env, timeout=20):
        async def probe():
            with open(os.devnull, 'w') as errors:
                async with AsyncExitStack() as stack:
                    reader, writer = await stack.enter_async_context(stdio_client(StdioServerParameters(command=command,args=args,env=env), errlog=errors))
                    session = await stack.enter_async_context(ClientSession(reader, writer))
                    await session.initialize()
                    result = await session.list_tools()
                    return [tool.name for tool in result.tools]
        try:
            tools = await asyncio.wait_for(probe(), timeout=timeout)
            return True, tools, f'{len(tools)} tools discovered'
        except Exception as error: return False, [], str(error) or type(error).__name__
