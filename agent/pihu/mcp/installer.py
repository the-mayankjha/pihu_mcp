"""Per-package installation with immutable releases and atomic activation."""
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import uuid
from pihu.mcp.artifacts import download_and_extract, select_artifact
from pihu.mcp.manifest import MCPRuntimeType
from pihu.mcp.registry import MCPRegistryClient
from pihu.mcp.resolver import MCPResolver
from pihu.mcp.package_store import PackageStore
from pihu.mcp.health import MCPHealthProbe
from pihu.mcp.locking import inventory_lock
from pihu.mcp.runtimes.python import PythonMCPRuntimeHandler
from pihu.mcp.runtimes.node import NodeMCPRuntimeHandler
from pihu.mcp.runtimes.binary import BinaryMCPRuntimeHandler, RemoteMCPRuntimeHandler

CORE_PACKAGES = {'pihu-file-mcp', 'pihu-system-mcp', 'pihu-project-mcp', 'pihu-web-search-mcp'}

class MCPInstaller:
    def __init__(self, pihu_mcp_dir=None, registry_client=None):
        self.package_store = PackageStore()
        self.base_dir = Path(pihu_mcp_dir) if pihu_mcp_dir else self.package_store.packages_dir
        self.servers_dir = self.base_dir / 'mcps'
        self.servers_dir.mkdir(parents=True, exist_ok=True)
        self.installed_json_path = self.package_store.state_path
        self.registry_client = registry_client or MCPRegistryClient()

    async def install(self, package_spec, callback=None):
        log = callback or (lambda message: None)
        candidate = None
        lock = None
        locked = False
        try:
            package_id, requested = MCPResolver.parse_spec(package_spec)
            if package_id in CORE_PACKAGES:
                return False, 'This core MCP is included with PIHU and updates with the app.', {}
            log('Resolving package manifest')
            manifest = await self.registry_client.fetch_manifest(package_id, requested)
            errors = manifest.validate()
            if errors: raise ValueError('; '.join(errors))
            if manifest.id != package_id or (requested not in ('latest', '*') and requested != manifest.version):
                raise ValueError('Registry returned a different package or version')
            minimum = manifest.compatibility.get('minimum_pihu_version')
            if minimum and os.environ.get('PIHU_APP_VERSION'):
                from packaging.version import Version
                if Version(os.environ['PIHU_APP_VERSION']) < Version(minimum): raise ValueError(f'This MCP requires PIHU {minimum} or later')
            if manifest.runtime != MCPRuntimeType.REMOTE and not manifest.artifacts:
                raise ValueError('No published download exists for this MCP yet. The repository must publish a versioned package first.')
            package_home = self.servers_dir / manifest.id
            lock = inventory_lock(package_home, timeout=1)
            lock.__enter__()
            locked = True
            # The directory never moves after venv/npm setup. Only inventory
            # activation changes; old versions survive failed updates and rollback.
            candidate = package_home / 'versions' / f'{manifest.version}-{uuid.uuid4().hex[:12]}'
            candidate.mkdir(parents=True)
            artifact = None
            if manifest.artifacts:
                select_artifact(manifest)
                log('Downloading and verifying package SHA-256')
                artifact = await asyncio.to_thread(download_and_extract, manifest, candidate)
            log('Preparing isolated runtime and dependencies')
            handler = self._get_runtime_handler(manifest.runtime)
            params = await handler.install(manifest, candidate)
            env = dict(manifest.entrypoint.env)
            required = manifest.permissions.env_vars_required
            missing = [name for name in required if not env.get(name) and not os.environ.get(name)]
            tools = []
            status = 'needs_configuration' if missing else 'ready'
            if not missing and manifest.runtime != MCPRuntimeType.REMOTE:
                log('Verifying MCP handshake and discovering tools')
                healthy, tools, detail = await MCPHealthProbe.probe_stdio_server(params['command'], params.get('args', []), {**os.environ, **env}, timeout=20)
                if not healthy: raise RuntimeError(detail)
            if manifest.runtime == MCPRuntimeType.REMOTE: status = 'configured'
            previous = next((record for record in self.package_store.list('mcp') if record['id'] == manifest.id), None)
            record = dict(id=manifest.id, name=manifest.name, display_name=manifest.display_name or manifest.name,
                version=manifest.version, runtime=manifest.runtime.value, transport=manifest.transport.value,
                enabled=not missing, status=status, command=params.get('command', ''), args=params.get('args', []),
                env=env, endpoint=params.get('endpoint'), tools=tools, install_path=str(candidate),
                manifest=manifest.to_dict(), description=manifest.description, author=manifest.author,
                artifact=artifact, missing_configuration=missing, last_error=None,
                installed_at=datetime.now(timezone.utc).isoformat(), previous=previous)
            # Don't nest an unbounded history inside installed.json.
            if previous: record['previous'] = {key: value for key, value in previous.items() if key != 'previous'}
            self.package_store.record(record, 'mcp')
            log('Package installed' if not missing else 'Package downloaded; account configuration is required')
            return True, f'Installed {manifest.id}@{manifest.version}: {status.replace("_", " ")}', record
        except Exception as error:
            if candidate: shutil.rmtree(candidate, ignore_errors=True)
            return False, str(error), {}
        finally:
            if lock and locked:
                try: lock.__exit__(None, None, None)
                except RuntimeError: pass

    async def uninstall(self, package_id):
        import re
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,63}', package_id): return False, 'Invalid package ID'
        if package_id in CORE_PACKAGES: return False, 'Core MCPs cannot be removed.'
        record = next((record for record in self.package_store.list('mcp') if record['id'] == package_id), None)
        if not record: return False, 'MCP is not installed'
        home = self.servers_dir / package_id
        with inventory_lock(home):
            # Remove only paths belonging to this package, never manifest-supplied
            # arbitrary directories or shared runtimes/account credentials.
            self.package_store.remove(package_id)
            versions = home / 'versions'
            if versions.is_dir() and not versions.is_symlink(): shutil.rmtree(versions)
        return True, f'Removed {package_id}'

    async def diagnose(self, package_id):
        record = next((record for record in self.package_store.list('mcp') if record['id'] == package_id), None)
        if not record: raise ValueError('MCP is not installed')
        required = record.get('manifest', {}).get('permissions', {}).get('env_vars_required', [])
        env = {**os.environ, **record.get('env', {})}
        missing = [name for name in required if not env.get(name)]
        if missing: return self.package_store.update(package_id, {'status':'needs_configuration','missing_configuration':missing,'last_error':'Required credentials are missing'})
        if not record.get('enabled', True): return self.package_store.update(package_id, {'status':'disabled','last_error':None})
        if record.get('runtime') == 'remote': return self.package_store.update(package_id, {'status':'configured','last_error':None})
        healthy, tools, detail = await MCPHealthProbe.probe_stdio_server(record['command'], record.get('args', []), env, timeout=20)
        return self.package_store.update(package_id, {'status':'ready' if healthy else 'error','tools':tools,'last_error':None if healthy else detail,'last_checked_at':datetime.now(timezone.utc).isoformat()})

    def configure(self, package_id, enabled=None, env=None):
        if package_id in CORE_PACKAGES: raise ValueError('Core MCP configuration is managed by PIHU')
        changes = {}
        if enabled is not None: changes.update(enabled=bool(enabled), status='installed' if enabled else 'disabled')
        if env is not None:
            if not isinstance(env, dict) or len(env) > 64 or any(not isinstance(k, str) or not isinstance(v, str) or len(v) > 8192 for k,v in env.items()): raise ValueError('Invalid MCP configuration')
            changes.update(env=env, status='installed')
        return self.package_store.update(package_id, changes)

    def rollback(self, package_id):
        if package_id in CORE_PACKAGES: raise ValueError('Core MCPs update with PIHU')
        import re
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,63}', package_id): raise ValueError('Invalid package ID')
        home = self.servers_dir / package_id
        with inventory_lock(home):
            record = next((record for record in self.package_store.list('mcp') if record['id'] == package_id), None)
            if not record or not record.get('previous'): raise ValueError('No previous package version is available')
            previous = record['previous']
            location = Path(previous['install_path']).resolve()
            if not location.is_relative_to((home / 'versions').resolve()) or not location.is_dir():
                raise ValueError('Previous package files are missing or outside the package directory')
            self.package_store.record(previous, 'mcp')
            return previous

    def _get_runtime_handler(self, runtime):
        return {MCPRuntimeType.PYTHON:PythonMCPRuntimeHandler, MCPRuntimeType.NODE:NodeMCPRuntimeHandler,
                MCPRuntimeType.BINARY:BinaryMCPRuntimeHandler, MCPRuntimeType.REMOTE:RemoteMCPRuntimeHandler}[runtime]()
    def _read_installed_manifest(self): return self.package_store.read()
    def _write_installed_manifest(self, data): self.package_store.write(data)
