"""Install Node MCP packages into an isolated package directory."""

import asyncio
import shutil
from pathlib import Path
from typing import Dict, Any

from pihu.mcp.manifest import MCPPackageManifest
from pihu.mcp.runtimes.base import BaseMCPRuntimeHandler
from pihu.mcp.runtimes.source import clone_source, resolve_entrypoint


class NodeMCPRuntimeHandler(BaseMCPRuntimeHandler):
    async def _run(self, *args: str, cwd: Path | None = None) -> None:
        proc = await asyncio.create_subprocess_exec(
            *args, cwd=str(cwd) if cwd else None,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            detail = stderr.decode(errors="replace").strip() or stdout.decode(errors="replace").strip()
            raise RuntimeError(detail or f"Command failed: {args[0]}")

    async def install(self, manifest: MCPPackageManifest, target_dir: Path) -> Dict[str, Any]:
        npm = shutil.which("npm")
        node = shutil.which("node")
        if not npm or not node:
            raise RuntimeError("Node MCP packages require Node.js 18+ and npm on PATH.")

        source_dir: Path | None = None
        entrypoint: Path | None = None
        if manifest.installation.method == "git":
            source_dir = await clone_source(manifest, target_dir)
            entrypoint = resolve_entrypoint(source_dir, manifest)
            package_dir = entrypoint.parent
            while package_dir != source_dir and not (package_dir / "package.json").is_file():
                package_dir = package_dir.parent
            if (package_dir / "package.json").is_file():
                await self._run(npm, "install", "--omit=dev", cwd=package_dir)
        else:
            package = manifest.installation.package or manifest.id
            await self._run(npm, "install", "--omit=dev", "--no-audit", "--no-fund", package, cwd=target_dir)
            if manifest.installation.entrypoint:
                relative = Path(manifest.installation.entrypoint)
                if relative.is_absolute() or ".." in relative.parts:
                    raise RuntimeError("The MCP manifest declares an unsafe Node entrypoint.")
                entrypoint = (target_dir / relative).resolve()
                if not entrypoint.is_relative_to(target_dir.resolve()) or not entrypoint.is_file():
                    raise RuntimeError("The installed MCP entrypoint was not found.")

        args = list(manifest.entrypoint.args)
        if entrypoint:
            command = node
            args.insert(0, str(entrypoint))
        else:
            command = manifest.entrypoint.command or shutil.which("npx") or "npx"
            if not args:
                args = ["-y", manifest.installation.package or manifest.id]
        return {"command": command, "args": args, "env": manifest.entrypoint.env or {}}
