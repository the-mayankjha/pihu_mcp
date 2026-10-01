"""
Node MCP Runtime Handler for isolated npm installation in ~/.pihu/mcp/servers/<id>/.
"""

import shutil
import asyncio
from pathlib import Path
from typing import Dict, Any
from pihu.mcp.manifest import MCPPackageManifest
from pihu.mcp.runtimes.base import BaseMCPRuntimeHandler


class NodeMCPRuntimeHandler(BaseMCPRuntimeHandler):
    """Manages Node.js MCP server installation inside isolated server directory."""

    async def install(self, manifest: MCPPackageManifest, target_dir: Path) -> Dict[str, Any]:
        pkg_spec = manifest.installation.package or manifest.id
        npm_cmd = shutil.which("npm") or shutil.which("pnpm") or "npm"

        # Initialize package.json if not present
        pkg_json = target_dir / "package.json"
        if not pkg_json.exists():
            pkg_json.write_text('{\n  "name": "' + manifest.id + '",\n  "private": true\n}\n')

        # Install node module locally into target_dir
        proc = await asyncio.create_subprocess_exec(
            npm_cmd, "install", pkg_spec,
            cwd=str(target_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()

        npx_cmd = shutil.which("npx") or "npx"
        args = manifest.entrypoint.args if manifest.entrypoint.args else ["-y", pkg_spec]

        return {
            "command": manifest.entrypoint.command or npx_cmd,
            "args": args,
            "env": manifest.entrypoint.env or {}
        }
