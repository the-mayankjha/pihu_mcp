"""Install Python MCP packages into an isolated environment."""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any

from pihu.mcp.manifest import MCPPackageManifest
from pihu.mcp.runtimes.base import BaseMCPRuntimeHandler
from pihu.mcp.runtimes.source import clone_source, resolve_entrypoint


class PythonMCPRuntimeHandler(BaseMCPRuntimeHandler):
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
        venv_dir = target_dir / ".venv"
        py_binary = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        await self._run(sys.executable, "-m", "venv", str(venv_dir))

        source_dir: Path | None = None
        entrypoint: Path | None = None
        if manifest.installation.method == "git" or manifest.installation.entrypoint:
            source_dir = await clone_source(manifest, target_dir)
            entrypoint = resolve_entrypoint(source_dir, manifest)

        dependencies = list(manifest.installation.dependencies)
        if manifest.installation.package:
            dependencies.append(manifest.installation.package)
        elif entrypoint:
            package_dir = entrypoint.parent
            if (package_dir / "pyproject.toml").is_file() or (package_dir / "setup.py").is_file():
                dependencies.append(str(package_dir))
            elif not dependencies:
                dependencies.append("mcp>=1.3.0,<2.0.0")

        if dependencies:
            await self._run(str(py_binary), "-m", "pip", "install", *dependencies)

        if entrypoint:
            command = str(py_binary)
            args = [str(entrypoint)]
        else:
            command = manifest.entrypoint.command or str(py_binary)
            args = list(manifest.entrypoint.args)
        return {"command": command, "args": args, "env": manifest.entrypoint.env or {}}
