#!/usr/bin/env python3
"""Build a platform MCP ZIP with dependencies and an immutable artifact descriptor."""
import argparse
import email
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile


def run(*args, cwd):
    subprocess.run(args, cwd=cwd, check=True)


def build(source, output, repository):
    manifest = json.loads((source / 'manifest.json').read_text())
    package_id, version = manifest['id'], manifest['version']
    if repository != manifest['repository']['url'].removeprefix('https://github.com/').removesuffix('.git'):
        raise ValueError('Repository does not match the package manifest')
    system = {'Darwin': 'macos', 'Windows': 'windows', 'Linux': 'linux'}[platform.system()]
    architecture = {'x86_64': 'x64', 'AMD64': 'x64', 'arm64': 'arm64', 'aarch64': 'arm64'}[platform.machine()]
    runtime = manifest['runtime']['type']
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='pihu-mcp-release-') as temporary:
        package = Path(temporary) / 'package'
        shutil.copytree(source, package, ignore=shutil.ignore_patterns('.git', '.github', '.venv', 'node_modules', '__pycache__', 'dist', '*.pyc', '.env', '.env.*', 'store', '*.db', '*.db-*', '*.sqlite*'))
        if runtime == 'python':
            if sys.version_info[:2] != (3, 11): raise ValueError('Build Python MCP releases with the shared runtime ABI: Python 3.11')
            wheels = package / 'wheelhouse'
            wheels.mkdir()
            run(sys.executable, '-m', 'pip', 'download', '--only-binary=:all:', '--dest', str(wheels), '-r', 'requirements.txt', cwd=package)
            locked = []
            for wheel in sorted(wheels.glob('*.whl')):
                with zipfile.ZipFile(wheel) as archive:
                    metadata = next(name for name in archive.namelist() if name.endswith('.dist-info/METADATA'))
                    headers = email.message_from_bytes(archive.read(metadata))
                locked.append(f"{headers['Name']}=={headers['Version']} --hash=sha256:{hashlib.sha256(wheel.read_bytes()).hexdigest()}")
            (package / 'requirements.lock').write_text('\n'.join(locked) + '\n')
        elif runtime == 'node':
            run('npm.cmd' if os.name == 'nt' else 'npm', 'ci', '--omit=dev', '--no-audit', '--no-fund', cwd=package)
        bridge = package / 'bridge-source'
        if bridge.is_dir():
            (package / 'native').mkdir(exist_ok=True)
            name = 'bridge.exe' if os.name == 'nt' else 'bridge'
            run('go', 'build', '-trimpath', '-ldflags=-s -w', '-o', str(package / 'native' / name), '.', cwd=bridge)
            shutil.rmtree(bridge)
        # Registry URLs/checksums are outside the archive, avoiding a checksum cycle.
        manifest['artifacts'] = []
        (package / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        name = f'{package_id}-{version}-{system}-{architecture}.zip'
        destination = output / name
        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for file in sorted(package.rglob('*')):
                if not file.is_file(): continue
                resolved = file.resolve()
                if not resolved.is_relative_to(package.resolve()): raise ValueError(f'Package contains an external link: {file}')
                relative = file.relative_to(package).as_posix()
                if '__pycache__' in file.parts or relative.startswith('node_modules/.bin/'): continue
                archive.write(resolved, relative)
        artifact = {'platform': system, 'architecture': architecture, 'format': 'zip',
            'url': f'https://github.com/{repository}/releases/download/v{version}/{name}',
            'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'size_bytes': destination.stat().st_size}
        (output / f'{system}-{architecture}.json').write_text(json.dumps(artifact, indent=2) + '\n')
        print(f'Built {destination}: {artifact["size_bytes"]} bytes')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path, default=Path('dist'))
    parser.add_argument('--repository', required=True)
    args = parser.parse_args()
    build(args.source.resolve(), args.output.resolve(), args.repository)
