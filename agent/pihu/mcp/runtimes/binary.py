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
        executable = target_dir / (manifest.installation.entrypoint or 'server')
        if not executable.resolve().is_relative_to(target_dir.resolve()) or not executable.is_file(): raise ValueError('Downloaded binary entrypoint is missing')
        executable.chmod(0o755)
        return {'command': str(executable), 'args': manifest.entrypoint.args, 'env': manifest.entrypoint.env}



class RemoteMCPRuntimeHandler(BaseMCPRuntimeHandler):
    """Handles HTTP/SSE streamable remote MCP server endpoints."""

    async def install(self, manifest: MCPPackageManifest, target_dir: Path) -> Dict[str, Any]:
        return {
            "endpoint": manifest.endpoint or manifest.installation.url,
            "transport": str(manifest.transport)
        }
