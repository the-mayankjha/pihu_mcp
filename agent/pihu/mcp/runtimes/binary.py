"""
Binary & Remote MCP Runtime Handlers.
"""

from pathlib import Path
from typing import Dict, Any
from pihu.mcp.manifest import MCPPackageManifest
from pihu.mcp.runtimes.base import BaseMCPRuntimeHandler


class BinaryMCPRuntimeHandler(BaseMCPRuntimeHandler):
    """Handles standalone executable MCP binaries."""

    async def install(self, manifest: MCPPackageManifest, target_dir: Path) -> Dict[str, Any]:
        return {
            "command": manifest.entrypoint.command,
            "args": manifest.entrypoint.args,
            "env": manifest.entrypoint.env or {}
        }


class RemoteMCPRuntimeHandler(BaseMCPRuntimeHandler):
    """Handles HTTP/SSE streamable remote MCP server endpoints."""

    async def install(self, manifest: MCPPackageManifest, target_dir: Path) -> Dict[str, Any]:
        return {
            "endpoint": manifest.endpoint or manifest.installation.url,
            "transport": str(manifest.transport)
        }
