import os
import sys
import platform
import subprocess
import psutil
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SystemMCP")

@mcp.tool()
def get_info() -> Dict[str, Any]:
    """Retrieve system information including OS, architecture, Python version, and CPU count."""
    return {
        "os": sys.platform,
        "platform": platform.platform(),
        "python_version": sys.version.split()[0],
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "memory_total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "memory_available_gb": round(psutil.virtual_memory().available / (1024 ** 3), 2),
    }

@mcp.tool()
def get_environment(var_name: str = "") -> Dict[str, str]:
    """Get environment variables. If var_name is provided, returns that specific variable."""
    if var_name:
        return {var_name: os.getenv(var_name, "")}
    # Exclude sensitive tokens from bulk dump
    return {k: v for k, v in os.environ.items() if not any(s in k.lower() for s in ["token", "key", "secret", "pass"])}

@mcp.tool()
def list_processes(name_filter: str = "") -> list:
    """List running system processes, optionally filtered by process name."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            info = proc.info
            if not name_filter or name_filter.lower() in info['name'].lower():
                processes.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return processes[:20]

@mcp.tool()
def run_shell(command: str) -> Dict[str, Any]:
    """Safely execute a shell command and return stdout/stderr output."""
    try:
        res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
        return {
            "exit_code": res.returncode,
            "stdout": res.stdout,
            "stderr": res.stderr
        }
    except Exception as e:
        return {"exit_code": -1, "error": str(e)}

@mcp.tool()
def send_notification(title: str, message: str) -> str:
    """Send a desktop notification to the user."""
    if sys.platform == "darwin":
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(["osascript", "-e", script])
        return "Notification sent via osascript."
    return "Desktop notification simulated."

if __name__ == "__main__":
    mcp.run(transport="stdio")
