"""Node packages run their downloaded entrypoint with the shared Node runtime."""
import os
from pathlib import Path
import shutil
class NodeMCPRuntimeHandler:
    async def install(self, manifest, target_dir):
        node = os.environ.get('PIHU_NODE_EXECUTABLE') or shutil.which('node')
        if not node: raise RuntimeError('The shared PIHU Node runtime is missing')
        if (target_dir / 'package.json').is_file() and not (target_dir / 'node_modules').is_dir():
            raise RuntimeError('Node release is incomplete: bundled node_modules is required')
        entrypoint = (target_dir / (manifest.installation.entrypoint or '')).resolve()
        if not entrypoint.is_relative_to(target_dir.resolve()) or not entrypoint.is_file(): raise ValueError('Node entrypoint is missing or unsafe')
        return {'command':node, 'args':[str(entrypoint), *manifest.entrypoint.args], 'env':manifest.entrypoint.env}
