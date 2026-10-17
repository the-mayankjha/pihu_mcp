"""Install Python MCP dependencies in their final, isolated environment."""
import os
import sys
from pathlib import Path
from pihu.mcp.runtimes.process import run

class PythonMCPRuntimeHandler:
    async def install(self, manifest, target_dir):
        environment = target_dir / '.venv'
        await run(sys.executable, '-m', 'venv', str(environment))
        python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        dependencies = list(manifest.installation.dependencies)
        requirements = target_dir / 'requirements.txt'
        locked = target_dir / 'requirements.lock'
        wheelhouse = target_dir / 'wheelhouse'
        if locked.is_file() and wheelhouse.is_dir():
            await run(str(python), '-m', 'pip', 'install', '--no-index', '--find-links', str(wheelhouse), '--require-hashes', '-r', str(locked), cwd=target_dir)
        elif requirements.is_file():
            raise ValueError('Python release must include a wheelhouse and hashed requirements.lock')
        if dependencies: raise ValueError('Dependencies must be bundled in wheelhouse and requirements.lock, not fetched during installation')
        relative = manifest.installation.entrypoint
        if not relative: raise ValueError('Python package must declare its entrypoint')
        entrypoint = (target_dir / relative).resolve()
        if not entrypoint.is_relative_to(target_dir.resolve()) or not entrypoint.is_file(): raise ValueError('Package entrypoint is missing or unsafe')
        return {'command':str(python),'args':[str(entrypoint), *manifest.entrypoint.args], 'env':manifest.entrypoint.env}
