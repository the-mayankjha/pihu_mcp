"""Download and validate GitHub sources referenced by an MCP manifest."""

import asyncio
from pathlib import Path
from urllib.parse import urlparse

from pihu.mcp.manifest import MCPPackageManifest


async def clone_source(manifest: MCPPackageManifest, target_dir: Path) -> Path:
    repository = manifest.repository.url if manifest.repository else manifest.installation.url
    branch = manifest.repository.branch if manifest.repository else None
    parsed = urlparse(repository or "")
    if parsed.scheme != "https" or parsed.hostname != "github.com" or len(parsed.path.strip("/").split("/")) != 2:
        raise RuntimeError("This registry package must reference an HTTPS GitHub repository.")

    source_dir = target_dir / "source"
    command = ["git", "clone", "--depth", "1"]
    if branch:
        if not all(char.isalnum() or char in "._/-" for char in branch) or branch.startswith("-") or ".." in branch:
            raise RuntimeError("The package declares an invalid Git branch.")
        command.extend(["--branch", branch])
    command.extend([repository, str(source_dir)])
    proc = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Could not download the MCP source: {stderr.decode(errors='replace').strip()}")
    return source_dir


def resolve_entrypoint(source_dir: Path, manifest: MCPPackageManifest) -> Path:
    relative = manifest.installation.entrypoint
    if not relative:
        raise RuntimeError("The MCP manifest does not declare an installation entrypoint.")
    entrypoint = (source_dir / relative).resolve()
    if not entrypoint.is_relative_to(source_dir.resolve()) or not entrypoint.is_file():
        raise RuntimeError("The MCP installation entrypoint is missing or outside its source repository.")
    return entrypoint
