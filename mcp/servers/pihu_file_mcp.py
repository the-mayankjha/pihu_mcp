"""
PIHU File MCP Server (pihu-file-mcp)

High-performance FastMCP server implementing comprehensive file operations:
discovery, metadata, reading, writing, line editing, searching, copying, moving, and trash deletion.
"""

import os
import re
import shutil
import hashlib
import fnmatch
import mimetypes
from pathlib import Path
from typing import List, Dict, Any, Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("pihu-file-mcp")

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB safety limit for full read


def _resolve_path(path_str: str) -> Path:
    """Resolve relative path to absolute path safely."""
    p = Path(path_str).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


@mcp.tool()
def list_directory(path: str = ".") -> List[Dict[str, Any]]:
    """List directory contents with detailed file metadata (size, type, modified time)."""
    target = _resolve_path(path)
    if not target.exists():
        raise FileNotFoundError(f"Directory not found: {path}")
    if not target.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {path}")

    items = []
    for entry in target.iterdir():
        try:
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size_bytes": stat.st_size if not entry.is_dir() else 0,
                "modified": stat.st_mtime,
                "extension": entry.suffix if not entry.is_dir() else "",
            })
        except Exception:
            pass

    return sorted(items, key=lambda x: (not x["is_dir"], x["name"].lower()))


@mcp.tool()
def tree(path: str = ".", depth: int = 3) -> str:
    """Generate a formatted directory tree visualization up to specified depth."""
    target = _resolve_path(path)
    if not target.exists():
        return f"Directory not found: {path}"

    lines = [f"{target.name}/"]

    def _build_tree(dir_path: Path, prefix: str, current_depth: int):
        if current_depth > depth:
            return
        try:
            entries = sorted(list(dir_path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
            count = len(entries)
            for i, entry in enumerate(entries):
                is_last = (i == count - 1)
                connector = "└── " if is_last else "├── "
                child_prefix = "    " if is_last else "│   "

                if entry.is_dir():
                    lines.append(f"{prefix}{connector}{entry.name}/")
                    _build_tree(entry, prefix + child_prefix, current_depth + 1)
                else:
                    lines.append(f"{prefix}{connector}{entry.name}")
        except Exception as e:
            lines.append(f"{prefix}[Error: {e}]")

    _build_tree(target, "", 1)
    return "\n".join(lines)


@mcp.tool()
def directory_exists(path: str) -> bool:
    """Check if a directory exists at specified path."""
    target = _resolve_path(path)
    return target.exists() and target.is_dir()


@mcp.tool()
def get_directory_size(path: str = ".") -> Dict[str, Any]:
    """Calculate total size of directory in bytes and file count."""
    target = _resolve_path(path)
    if not target.exists() or not target.is_dir():
        raise FileNotFoundError(f"Directory not found: {path}")

    total_bytes = 0
    file_count = 0
    dir_count = 0

    for root, dirs, files in os.walk(target):
        dir_count += len(dirs)
        for f in files:
            fp = Path(root) / f
            try:
                if not fp.is_symlink():
                    total_bytes += fp.stat().st_size
                    file_count += 1
            except Exception:
                pass

    size_mb = round(total_bytes / (1024 * 1024), 2)
    return {
        "path": str(target),
        "total_bytes": total_bytes,
        "size_mb": size_mb,
        "file_count": file_count,
        "dir_count": dir_count,
    }


@mcp.tool()
def stat_file(path: str) -> Dict[str, Any]:
    """Get complete metadata for a file (size, line count, extension, permissions, modified time)."""
    target = _resolve_path(path)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {path}")

    stat = target.stat()
    mime, _ = mimetypes.guess_type(str(target))

    line_count = 0
    if target.is_file() and stat.st_size < MAX_FILE_SIZE_BYTES:
        try:
            with open(target, "r", encoding="utf-8", errors="ignore") as f:
                line_count = sum(1 for _ in f)
        except Exception:
            pass

    return {
        "filename": target.name,
        "path": str(target),
        "is_dir": target.is_dir(),
        "is_file": target.is_file(),
        "size_bytes": stat.st_size,
        "extension": target.suffix,
        "mime_type": mime or "application/octet-stream",
        "line_count": line_count,
        "created_time": stat.st_ctime,
        "modified_time": stat.st_mtime,
    }


@mcp.tool()
def get_file_hash(path: str, algorithm: str = "sha256") -> str:
    """Calculate cryptographic hash (sha256 or md5) of a file for integrity check."""
    target = _resolve_path(path)
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    algo = getattr(hashlib, algorithm.lower(), hashlib.sha256)()
    with open(target, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            algo.update(chunk)
    return algo.hexdigest()


@mcp.tool()
def read_file(path: str, max_lines: int = 500) -> str:
    """Read complete or partial text contents of a file."""
    target = _resolve_path(path)
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    if target.stat().st_size > MAX_FILE_SIZE_BYTES:
        return f"File is too large ({target.stat().st_size} bytes). Use read_lines or read_head instead."

    lines = []
    with open(target, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            if i > max_lines:
                lines.append(f"\n... [Truncated at {max_lines} lines]")
                break
            lines.append(line)

    return "".join(lines)


@mcp.tool()
def read_lines(path: str, start_line: int = 1, end_line: int = 100) -> str:
    """Read a specific line range from a text file (1-indexed, inclusive)."""
    target = _resolve_path(path)
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    if start_line < 1:
        start_line = 1

    selected = []
    with open(target, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            if i >= start_line and i <= end_line:
                selected.append(f"{i}: {line}")
            elif i > end_line:
                break

    return "".join(selected) if selected else f"No lines found in range [{start_line}, {end_line}]"


@mcp.tool()
def read_head(path: str, n_lines: int = 20) -> str:
    """Read first N lines of a file."""
    return read_lines(path, start_line=1, end_line=n_lines)


@mcp.tool()
def read_tail(path: str, n_lines: int = 20) -> str:
    """Read last N lines of a file."""
    target = _resolve_path(path)
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    with open(target, "r", encoding="utf-8", errors="replace") as f:
        all_lines = f.readlines()

    tail_lines = all_lines[-n_lines:] if len(all_lines) >= n_lines else all_lines
    start_idx = max(1, len(all_lines) - len(tail_lines) + 1)

    result = []
    for idx, line in enumerate(tail_lines, start=start_idx):
        result.append(f"{idx}: {line}")
    return "".join(result)


@mcp.tool()
def create_file(path: str, content: str = "") -> str:
    """Create a new file at path with optional initial content."""
    target = _resolve_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Successfully created file: {target}"


@mcp.tool()
def create_directory(path: str) -> str:
    """Create a directory and any necessary parent directories."""
    target = _resolve_path(path)
    target.mkdir(parents=True, exist_ok=True)
    return f"Successfully created directory: {target}"


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write content to file, creating or completely overwriting existing file."""
    target = _resolve_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Successfully wrote {len(content)} characters to {target}"


@mcp.tool()
def append_file(path: str, content: str) -> str:
    """Append text content to the end of an existing file."""
    target = _resolve_path(path)
    if not target.exists():
        return create_file(path, content)

    with open(target, "a", encoding="utf-8") as f:
        f.write(content)
    return f"Successfully appended {len(content)} characters to {target}"


@mcp.tool()
def replace_text(path: str, target_text: str, replacement_text: str) -> str:
    """Search and replace exact target text string inside a file."""
    target = _resolve_path(path)
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    with open(target, "r", encoding="utf-8", errors="replace") as f:
        full_text = f.read()

    if target_text not in full_text:
        return f"Target text '{target_text[:30]}...' not found in {target.name}"

    occurrences = full_text.count(target_text)
    new_text = full_text.replace(target_text, replacement_text)

    with open(target, "w", encoding="utf-8") as f:
        f.write(new_text)

    return f"Replaced {occurrences} occurrence(s) in {target.name}"


@mcp.tool()
def copy_file(src: str, dst: str) -> str:
    """Copy a file or directory from src to dst."""
    src_path = _resolve_path(src)
    dst_path = _resolve_path(dst)

    if not src_path.exists():
        raise FileNotFoundError(f"Source path not found: {src}")

    dst_path.parent.mkdir(parents=True, exist_ok=True)

    if src_path.is_dir():
        shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        return f"Copied directory {src_path} -> {dst_path}"
    else:
        shutil.copy2(src_path, dst_path)
        return f"Copied file {src_path} -> {dst_path}"


@mcp.tool()
def move_file(src: str, dst: str) -> str:
    """Move or rename a file/directory from src to dst."""
    src_path = _resolve_path(src)
    dst_path = _resolve_path(dst)

    if not src_path.exists():
        raise FileNotFoundError(f"Source path not found: {src}")

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_path), str(dst_path))
    return f"Moved {src_path} -> {dst_path}"


@mcp.tool()
def trash_file(path: str) -> str:
    """Safely move a file or directory to the local .trash directory."""
    target = _resolve_path(path)
    if not target.exists():
        raise FileNotFoundError(f"Path not found: {path}")

    trash_dir = Path.cwd() / ".trash"
    trash_dir.mkdir(exist_ok=True)

    dst = trash_dir / target.name
    if dst.exists():
        dst = trash_dir / f"{target.stem}_{int(os.path.getmtime(target))}{target.suffix}"

    shutil.move(str(target), str(dst))
    return f"Moved {target.name} to trash: {dst}"


@mcp.tool()
def find_files(pattern: str = "*", path: str = ".", max_results: int = 50) -> List[Dict[str, Any]]:
    """Search files matching glob pattern (e.g. '*.py', 'invoice*.pdf') starting at path."""
    target = _resolve_path(path)
    if not target.exists():
        return []

    results = []
    for root, dirs, files in os.walk(target):
        for name in files + dirs:
            if fnmatch.fnmatch(name, pattern):
                fp = Path(root) / name
                try:
                    rel = fp.relative_to(target)
                    results.append({
                        "name": name,
                        "path": str(fp),
                        "relative_path": str(rel),
                        "is_dir": fp.is_dir(),
                        "size_bytes": fp.stat().st_size if fp.is_file() else 0,
                    })
                    if len(results) >= max_results:
                        return results
                except Exception:
                    pass
    return results


@mcp.tool()
def grep_search(query: str, path: str = ".", case_sensitive: bool = False, max_results: int = 50) -> List[Dict[str, Any]]:
    """Search for exact text query inside all text files in a directory."""
    target = _resolve_path(path)
    if not target.exists():
        return []

    flags = 0 if case_sensitive else re.IGNORECASE
    regex = re.compile(re.escape(query), flags)

    matches = []

    for root, dirs, files in os.walk(target):
        # Skip .git, .venv, __pycache__, node_modules
        dirs[:] = [d for d in dirs if d not in {".git", ".venv", "__pycache__", "node_modules", ".trash"}]

        for f in files:
            fp = Path(root) / f
            try:
                if fp.stat().st_size > MAX_FILE_SIZE_BYTES:
                    continue
                with open(fp, "r", encoding="utf-8", errors="ignore") as file_obj:
                    for line_num, line in enumerate(file_obj, 1):
                        if regex.search(line):
                            matches.append({
                                "file": str(fp),
                                "line_number": line_num,
                                "line_content": line.strip()[:200],
                            })
                            if len(matches) >= max_results:
                                return matches
            except Exception:
                pass

    return matches


if __name__ == "__main__":
    mcp.run()
