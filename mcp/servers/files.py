import os
import shutil
from pathlib import Path
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("FilesMCP")

@mcp.tool()
def list_directory(directory_path: str = ".") -> List[Dict[str, Any]]:
    """List directory contents with file size and type information."""
    target = Path(directory_path).resolve()
    if not target.exists():
        raise FileNotFoundError(f"Path not found: {directory_path}")

    items = []
    for p in target.iterdir():
        items.append({
            "name": p.name,
            "path": str(p),
            "is_directory": p.is_dir(),
            "size_bytes": p.stat().st_size if p.is_file() else 0
        })
    return items

@mcp.tool()
def read_file(file_path: str) -> str:
    """Read full text content from a file."""
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    return path.read_text(encoding="utf-8")

@mcp.tool()
def write_file(file_path: str, content: str) -> str:
    """Write text content to a file. Overwrites if file exists."""
    path = Path(file_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"Successfully wrote {len(content)} bytes to {file_path}"

@mcp.tool()
def search_files(directory_path: str = ".", pattern: str = "*") -> List[str]:
    """Search files in directory matching glob pattern."""
    target = Path(directory_path).resolve()
    return [str(p) for p in target.rglob(pattern) if p.is_file()][:50]

@mcp.tool()
def move_file(source_path: str, destination_path: str) -> str:
    """Move or rename a file or directory."""
    shutil.move(source_path, destination_path)
    return f"Moved {source_path} to {destination_path}"

@mcp.tool()
def copy_file(source_path: str, destination_path: str) -> str:
    """Copy a file from source to destination."""
    shutil.copy2(source_path, destination_path)
    return f"Copied {source_path} to {destination_path}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
