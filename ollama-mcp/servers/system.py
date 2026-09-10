import os
import platform
import shutil


import psutil
from mcp.server import MCPServer
from datetime import datetime

mcp = MCPServer("System")


@mcp.tool()
def get_current_time() -> dict:
    """Get the current local date and time."""
    now = datetime.now()

    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day": now.strftime("%A"),
        "formatted": now.strftime("%A, %B %d, %Y at %I:%M:%S %p"),
    }


@mcp.tool()
def get_system_info() -> dict:
    """Get operating system, CPU, RAM, disk and Python information."""

    memory = psutil.virtual_memory()
    disk = shutil.disk_usage(os.path.expanduser("~"))

    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "cpu_usage_percent": psutil.cpu_percent(interval=0.2),
        "memory_total_gb": round(memory.total / 1024**3, 2),
        "memory_used_gb": round(memory.used / 1024**3, 2),
        "memory_available_gb": round(memory.available / 1024**3, 2),
        "memory_percent": memory.percent,
        "disk_total_gb": round(disk.total / 1024**3, 2),
        "disk_free_gb": round(disk.free / 1024**3, 2),
        "disk_percent": round(
            (disk.used / disk.total) * 100,
            1,
        ),
    }


@mcp.tool()
def get_battery() -> dict:
    """Get the current battery percentage and charging status."""

    battery = psutil.sensors_battery()

    if battery is None:
        return {
            "available": False,
            "message": "Battery information is not available."
        }

    result = {
        "available": True,
        "percentage": battery.percent,
        "charging": battery.power_plugged,
    }

    if battery.secsleft > 0:
        result["time_left_minutes"] = round(
            battery.secsleft / 60
        )
    else:
        result["time_left_minutes"] = None

    return result


@mcp.tool()
def get_environment() -> dict:
    """Get basic non-sensitive environment information."""

    return {
        "home": os.path.expanduser("~"),
        "current_directory": os.getcwd(),
        "shell": os.environ.get("SHELL"),
        "username": os.environ.get("USER"),
    }


if __name__ == "__main__":
    mcp.run()
