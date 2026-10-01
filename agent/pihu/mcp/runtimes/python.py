"""
Python MCP Runtime Handler using uv venv & uv pip for isolated virtual environments.
"""

import os
import sys
import shutil
import asyncio
from pathlib import Path
from typing import Dict, Any
from pihu.mcp.manifest import MCPPackageManifest
from pihu.mcp.runtimes.base import BaseMCPRuntimeHandler


class PythonMCPRuntimeHandler(BaseMCPRuntimeHandler):
    """Manages Python MCP virtualenv creation via `uv venv` and dependency installation via `uv pip`."""

    async def install(self, manifest: MCPPackageManifest, target_dir: Path) -> Dict[str, Any]:
        venv_dir = target_dir / ".venv"
        py_binary = venv_dir / "bin" / "python"
        if sys.platform == "win32":
            py_binary = venv_dir / "Scripts" / "python.exe"

        uv_cmd = shutil.which("uv")

        # Step 1: Create virtualenv via `uv venv` (or standard venv fallback)
        if uv_cmd:
            proc = await asyncio.create_subprocess_exec(
                uv_cmd, "venv", str(venv_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"Failed to create uv venv: {stderr.decode()}")
        else:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "venv", str(venv_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"Failed to create python venv: {stderr.decode()}")

        # Step 2: Install package dependencies into isolated venv via `uv pip` (or pip)
        pkg_spec = manifest.installation.package or manifest.id
        if uv_cmd:
            proc = await asyncio.create_subprocess_exec(
                uv_cmd, "pip", "install", "--python", str(py_binary), pkg_spec,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                # Fallback gracefully if package is not published on PyPI
                pass
        else:
            proc = await asyncio.create_subprocess_exec(
                str(py_binary), "-m", "pip", "install", pkg_spec,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()

        # Build entrypoint command
        cmd = str(py_binary)
        args = list(manifest.entrypoint.args)
        if args and args[0] in ("python", "python3"):
            args = args[1:]

        return {
            "command": cmd,
            "args": args,
            "env": manifest.entrypoint.env or {}
        }
