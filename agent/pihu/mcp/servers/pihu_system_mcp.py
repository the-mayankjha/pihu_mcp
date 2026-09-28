"""
PIHU System MCP Server (pihu-system-mcp)

High-performance FastMCP server providing system awareness and control tools:
system info, system snapshot, realtime status (CPU, RAM, Disk, Battery), datetime, process listing, shell execution, notifications.
"""

import sys
import os
import psutil
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("pihu-system-mcp")


@mcp.tool()
def get_system_info() -> Dict[str, Any]:
    """Retrieve system identity, OS, kernel, CPU model, architecture, Python version, and uptime."""
    import platform

    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime_seconds = (datetime.now() - boot_time).total_seconds()
    uptime_hours = round(uptime_seconds / 3600, 1)

    return {
        "os": sys.platform,
        "os_name": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "python_version": sys.version.split()[0],
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "boot_time": boot_time.isoformat(),
        "uptime_hours": uptime_hours,
    }


@mcp.tool()
def get_system_status() -> Dict[str, Any]:
    """Get real-time snapshot of CPU load %, Memory (RAM) usage, Disk usage %, and Battery."""
    cpu_pct = psutil.cpu_percent(interval=0.2)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    battery_info = None
    if hasattr(psutil, "sensors_battery"):
        try:
            batt = psutil.sensors_battery()
            if batt:
                battery_info = {
                    "percent": batt.percent,
                    "power_plugged": batt.power_plugged,
                    "secs_left": batt.secsleft if batt.secsleft > 0 else "unknown",
                }
        except Exception:
            pass

    return {
        "cpu_percent": cpu_pct,
        "memory": {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "percent_used": mem.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent_used": disk.percent,
        },
        "battery": battery_info,
    }


@mcp.tool()
def get_system_snapshot() -> Dict[str, Any]:
    """Get a unified, comprehensive snapshot of system identity, hardware resources, storage, and current datetime in a single call."""
    info = get_system_info()
    status = get_system_status()
    time_info = get_current_time("Asia/Kolkata")

    return {
        "system": info,
        "status": status,
        "time": time_info,
        "health": "Healthy" if status["memory"]["percent_used"] < 95 and status["disk"]["percent_used"] < 95 else "Warning",
    }


@mcp.tool()
def get_current_time(timezone: str = "Asia/Kolkata") -> Dict[str, Any]:
    """Get current time, date, day of week, and timezone offset for a specified IANA timezone."""
    try:
        tz = ZoneInfo(timezone)
    except Exception:
        tz = ZoneInfo("UTC")

    now = datetime.now(tz)
    return {
        "timezone": timezone,
        "datetime": now.isoformat(),
        "formatted": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "day_of_week": now.strftime("%A"),
        "is_dst": bool(now.dst()),
    }


@mcp.tool()
def list_processes(filter_name: str = "", top_n: int = 15) -> List[Dict[str, Any]]:
    """List active running processes with PID, name, CPU %, and Memory % usage."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "username"]):
        try:
            p_name = p.info.get("name") or ""
            if filter_name and filter_name.lower() not in p_name.lower():
                continue
            procs.append({
                "pid": p.info.get("pid"),
                "name": p_name,
                "cpu_percent": round(p.info.get("cpu_percent") or 0.0, 1),
                "memory_percent": round(p.info.get("memory_percent") or 0.0, 1),
                "username": p.info.get("username") or "",
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    procs.sort(key=lambda x: x["memory_percent"], reverse=True)
    return procs[:top_n]


@mcp.tool()
def run_shell(command: str, timeout_seconds: int = 15) -> Dict[str, Any]:
    """Safely execute a shell command and return stdout/stderr/exit code."""
    forbidden = ["rm -rf /", "mkfs", "dd if=/dev/zero", ":(){ :|:& };:"]
    if any(f in command for f in forbidden):
        return {"exit_code": -1, "stdout": "", "stderr": "Command blocked by security policy."}

    try:
        res = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=str(os.getcwd())
        )
        return {
            "exit_code": res.returncode,
            "stdout": res.stdout[:5000],
            "stderr": res.stderr[:2000],
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "stdout": "", "stderr": f"Command timed out after {timeout_seconds}s"}
    except Exception as e:
        return {"exit_code": -1, "stdout": "", "stderr": str(e)}


@mcp.tool()
def send_notification(title: str, message: str) -> str:
    """Send a native OS desktop notification."""
    if sys.platform == "darwin":
        script = f'display notification "{message}" with title "{title}"'
        try:
            subprocess.run(["osascript", "-e", script], check=True)
            return f"Notification sent: '{title}'"
        except Exception as e:
            return f"Failed to send notification: {e}"
    else:
        return f"Desktop notification stub: [{title}] {message}"


if __name__ == "__main__":
    mcp.run()
