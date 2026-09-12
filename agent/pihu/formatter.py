"""
PIHU Human Response Formatter — Converts raw MCP JSON output into warm, natural, human-friendly responses.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any


def format_human_response(tool_name: str, raw_output: str, fast_args: Optional[Dict[str, Any]] = None) -> str:
    """Format raw MCP tool JSON output into natural, friendly human language."""
    if not raw_output:
        return ""

    try:
        data = json.loads(raw_output)
    except Exception:
        return str(raw_output)

    if not isinstance(data, (dict, list)):
        return str(raw_output)

    args = fast_args or {}
    focus = (args.get("focus") or "").lower()

    # 1. get_current_time
    if tool_name == "get_current_time":
        dt_raw = data.get("datetime", "")
        tz = data.get("timezone", "Asia/Kolkata")
        day = data.get("day_of_week", "")
        formatted_time = data.get("formatted_time", "")

        try:
            # Parse ISO datetime (e.g. 2026-09-11T01:57:20.702955+05:30)
            dt = datetime.fromisoformat(dt_raw.replace("Z", "+00:00"))
            friendly_date = dt.strftime("%A, %B %d, %Y")
            friendly_time = dt.strftime("%I:%M:%S %p").lstrip("0")
            return f"It's {friendly_time} on {friendly_date} ({tz})."
        except Exception:
            return f"It's {formatted_time or dt_raw} ({day}) in {tz}."

    # 2. get_system_status
    if tool_name == "get_system_status":
        cpu = data.get("cpu_percent", 0.0)
        mem = data.get("memory", {})
        disk = data.get("disk", {})
        batt = data.get("battery", {})

        if "memory" in focus or "ram" in focus:
            total_gb = mem.get("total_gb", 0)
            used_gb = mem.get("used_gb", 0)
            avail_gb = mem.get("available_gb", 0)
            pct = mem.get("percent_used", 0)
            return (
                f"You have {total_gb} GB of RAM in total. Currently, {used_gb} GB ({pct}%) "
                f"is in use, leaving about {avail_gb} GB available."
            )

        if "cpu" in focus or "processor" in focus:
            return f"Your CPU utilization is currently at {cpu}%."

        if "disk" in focus or "storage" in focus or "space" in focus:
            total_gb = disk.get("total_gb", 0)
            used_gb = disk.get("used_gb", 0)
            free_gb = disk.get("free_gb", 0)
            pct = disk.get("percent_used", 0)
            return (
                f"Your disk storage has {free_gb} GB free out of {total_gb} GB ({pct}% used)."
            )

        if "battery" in focus or "power" in focus:
            if batt and isinstance(batt, dict):
                pct = batt.get("percent", 0)
                plugged = "plugged in" if batt.get("power_plugged") else "running on battery"
                return f"Your battery is at {pct}% ({plugged})."
            return "Battery information is not available on this system."

        # Default overall system status
        mem_used = mem.get("used_gb", 0)
        mem_total = mem.get("total_gb", 0)
        mem_pct = mem.get("percent_used", 0)
        disk_free = disk.get("free_gb", 0)
        disk_total = disk.get("total_gb", 0)

        return (
            f"Here is your current system status:\n"
            f"• CPU Load: {cpu}%\n"
            f"• Memory (RAM): {mem_used} GB / {mem_total} GB ({mem_pct}% used)\n"
            f"• Disk Storage: {disk_free} GB free / {disk_total} GB total"
        )

    # 3. get_system_snapshot
    if tool_name == "get_system_snapshot":
        sys_info = data.get("system", {})
        status = data.get("status", {})
        time_info = data.get("time", {})
        os_name = sys_info.get("os", "macOS")
        cpu_cores = sys_info.get("cpu_cores_physical", 10)
        mem = status.get("memory", {})
        cpu = status.get("cpu_percent", 0.0)

        return (
            f"System Overview ({os_name}, {cpu_cores}-core CPU):\n"
            f"• CPU Utilization: {cpu}%\n"
            f"• Memory: {mem.get('used_gb', 0)} GB used / {mem.get('total_gb', 0)} GB total ({mem.get('percent_used', 0)}%)\n"
            f"• Current Time: {time_info.get('formatted_time', '')} ({time_info.get('day_of_week', '')})"
        )

    # 4. list_directory
    if tool_name == "list_directory":
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "items" in data:
            items = data["items"]
        elif isinstance(data, dict) and "result" in data:
            items = data["result"]
        else:
            return str(raw_output)

        if not items:
            return "The directory is empty."

        path_name = (
            args.get("path")
            or (data.get("path") if isinstance(data, dict) else None)
            or "."
        )

        dirs = [item for item in items if item.get("is_dir") or item.get("type") == "directory"]
        files = [item for item in items if not (item.get("is_dir") or item.get("type") == "directory")]

        all_entries = dirs + files
        total = len(all_entries)

        tree_lines = [f"📁 **{path_name}** ({total} items)\n"]
        for idx, entry in enumerate(all_entries):
            connector = "└── " if idx == total - 1 else "├── "
            is_directory = entry.get("is_dir") or entry.get("type") == "directory"
            name = entry.get("name") or entry.get("filename") or str(entry)
            icon = "📁 " if is_directory else "📄 "
            suffix = "/" if is_directory and not name.endswith("/") else ""
            tree_lines.append(f"  {connector}{icon}{name}{suffix}")

        return "\n".join(tree_lines)

    return str(raw_output)
