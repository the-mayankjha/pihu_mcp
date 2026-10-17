"""Bound package setup processes and avoid Windows console popups."""
import asyncio
import os
import subprocess
async def run(*arguments, cwd=None):
    flags = {'creationflags':subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
    environment = dict(os.environ)
    # Runtime inference is offline; explicit package installation is allowed to
    # fetch declared dependencies without inheriting a model-cache policy.
    environment.pop('HF_HUB_OFFLINE', None)
    process = await asyncio.create_subprocess_exec(*arguments, cwd=str(cwd) if cwd else None, env=environment, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, **flags)
    try: stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600)
    except BaseException:
        process.kill(); await process.wait(); raise
    if process.returncode: raise RuntimeError((stderr or stdout).decode(errors='replace')[-4000:])
