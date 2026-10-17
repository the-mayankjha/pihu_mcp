"""Serialize inventory mutations across desktop and CLI processes."""
from contextlib import contextmanager
from pathlib import Path
import os
import time

@contextmanager
def inventory_lock(directory: Path, timeout=15):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.packages.lock').open('a+b') as handle:
        if handle.tell() == 0: handle.write(b'0'); handle.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                handle.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() > deadline: raise RuntimeError('Another package operation is still running')
                time.sleep(0.1)
        try: yield
        finally:
            handle.seek(0)
            if os.name == 'nt': msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
