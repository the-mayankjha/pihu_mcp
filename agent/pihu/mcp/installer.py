"""
Transactional MCP Package Installer.
Executes atomic installation pipeline with rollback capabilities on failure.
"""

import os
import shutil
import hashlib
import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from pihu.mcp.manifest import MCPPackageManifest, MCPRuntimeType
from pihu.mcp.registry import MCPRegistryClient
from pihu.mcp.resolver import MCPResolver
from pihu.mcp.health import MCPHealthProbe
from pihu.mcp.package_store import PackageStore
from pihu.mcp.runtimes.python import PythonMCPRuntimeHandler
from pihu.mcp.runtimes.node import NodeMCPRuntimeHandler
from pihu.mcp.runtimes.binary import BinaryMCPRuntimeHandler, RemoteMCPRuntimeHandler


class MCPInstaller:
    """Atomic MCP Package Installer executing transactional server installs."""

    def __init__(self, pihu_mcp_dir: Optional[Path] = None, registry_client: Optional[MCPRegistryClient] = None):
        self.package_store = PackageStore()
        self.base_dir = pihu_mcp_dir or self.package_store.packages_dir
        self.servers_dir = self.base_dir / "mcps" if pihu_mcp_dir else self.package_store.mcps_dir
        self.installed_json_path = self.package_store.state_path
        self.registry_client = registry_client or MCPRegistryClient()

        # Ensure base directories exist
        self.servers_dir.mkdir(parents=True, exist_ok=True)
        if not self.installed_json_path.exists():
            self._write_installed_manifest({})

    async def install(self, package_spec: str, callback: Optional[Any] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Transactional installation pipeline:
        1. Resolve package spec & fetch manifest
        2. Validate manifest schema
        3. Create temporary sandbox directory
        4. Execute runtime installer (uv / npm)
        5. Verify declared package metadata
        6. Probe server health & discover tools
        7. Atomic commit to ~/.pihu/mcp/installed.json
        8. Rollback sandbox if any step fails
        """
        def _log(msg: str):
            if callback:
                callback(msg)

        mcp_id, version_req = MCPResolver.parse_spec(package_spec)
        _log(f"Resolving '{mcp_id}' (version: {version_req})...")

        try:
            manifest = await self.registry_client.fetch_manifest(mcp_id, version_req)
        except Exception as e:
            return False, f"Resolution failed: {str(e)}", {}

        # Step 2: Validate Manifest
        _log("Validating package manifest...")
        errors = manifest.validate()
        if errors:
            return False, f"Manifest validation error: {', '.join(errors)}", {}

        target_dir = self.servers_dir / manifest.id
        temp_dir = self.servers_dir / f".tmp_{manifest.id}_{os.getpid()}"

        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Step 3: Run Runtime Installer in temp sandbox
            _log(f"Building runtime environment for '{manifest.runtime}'...")
            handler = self._get_runtime_handler(manifest.runtime)
            exec_params = await handler.install(manifest, temp_dir)

            if manifest.installation.checksum_sha256:
                raise RuntimeError("This source installer cannot verify a package checksum; the package was not installed.")

            # Step 5: Save manifest into server folder
            (temp_dir / "manifest.json").write_text(json.dumps(manifest.to_dict(), indent=2))

            # Step 6: Perform Health probe & tool discovery if stdio
            tools_discovered = manifest.tools_provided
            if manifest.runtime != MCPRuntimeType.REMOTE:
                _log("Running health check & discovering tools...")
                command = exec_params.get("command", "")
                args = exec_params.get("args", [])
                env = exec_params.get("env", os.environ.copy())

                healthy, probe_tools, probe_msg = await MCPHealthProbe.probe_stdio_server(command, args, env)
                if not healthy:
                    raise RuntimeError(f"MCP health check failed: {probe_msg}")
                if probe_tools:
                    tools_discovered = probe_tools
                _log(f"Health check passed! {len(tools_discovered)} tools discovered.")

            # Step 7: Atomic Commit (Move temp_dir to the shared package directory).
            _log("Registering MCP in the shared PIHU package inventory...")
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            temp_dir.rename(target_dir)

            server_record = {
                "id": manifest.id,
                "name": manifest.name,
                "version": manifest.version,
                "runtime": str(manifest.runtime),
                "transport": str(manifest.transport),
                "enabled": True,
                "command": str(exec_params.get("command", "")).replace(str(temp_dir), str(target_dir)),
                "args": [str(arg).replace(str(temp_dir), str(target_dir)) for arg in exec_params.get("args", [])],
                "env": exec_params.get("env", {}),
                "endpoint": exec_params.get("endpoint"),
                "tools": tools_discovered,
                "installed_at": datetime.now(timezone.utc).isoformat(),
                "install_path": str(target_dir),
                "display_name": manifest.display_name or manifest.name,
                "description": manifest.description,
                "author": manifest.author,
                "tool_definitions": manifest.tool_definitions,
                "manifest": manifest.to_dict(),
            }

            self.package_store.record(server_record, "mcp")

            _log(f"Successfully installed {manifest.id}@{manifest.version}!")
            return True, f"Installed {manifest.id}@{manifest.version} with {len(tools_discovered)} tools.", server_record

        except Exception as e:
            _log(f"Installation failed: {str(e)}. Rolling back...")
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            return False, f"Installation error: {str(e)}", {}

    async def uninstall(self, mcp_id: str) -> Tuple[bool, str]:
        """Removes an installed MCP server and cleans up its directory."""
        record = next((item for item in self.package_store.list("mcp") if item.get("id") == mcp_id), None)
        if record is None:
            return False, f"MCP '{mcp_id}' is not installed."

        self.package_store.remove(mcp_id)
        target_dir = Path(record.get("install_path", self.servers_dir / mcp_id))
        if not target_dir.exists():
            # Remove packages installed by the pre-market MCP installer.
            target_dir = Path.home() / ".pihu" / "mcp" / "servers" / mcp_id
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)

        return True, f"MCP '{mcp_id}' uninstalled successfully."

    def _get_runtime_handler(self, runtime: MCPRuntimeType):
        if runtime == MCPRuntimeType.PYTHON:
            return PythonMCPRuntimeHandler()
        elif runtime == MCPRuntimeType.NODE:
            return NodeMCPRuntimeHandler()
        elif runtime == MCPRuntimeType.BINARY:
            return BinaryMCPRuntimeHandler()
        elif runtime == MCPRuntimeType.REMOTE:
            return RemoteMCPRuntimeHandler()
        return PythonMCPRuntimeHandler()

    def _read_installed_manifest(self) -> Dict[str, Any]:
        return self.package_store.read()

    def _write_installed_manifest(self, data: Dict[str, Any]) -> None:
        self.package_store.write(data)
