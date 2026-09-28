from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional
from rich.box import ROUNDED
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown


def get_server_icon_color(server: str) -> tuple[str, str]:
    """Return unicode icon and color for an MCP server (strictly no emojis)."""
    meta = {
        "pihu-file-mcp": ("◫", "#89b4fa"),       # folder / file icon symbol
        "pihu-system-mcp": ("⚙", "#a6e3a1"),     # gear icon symbol
        "filesystem": ("◫", "#89b4fa"),
        "memory": ("◆", "#cba6f7"),              # diamond icon symbol
        "fetch": ("↗", "#94e2d5"),               # arrow icon symbol
        "time": ("◷", "#f9e2af"),                # clock icon symbol
        "web-search": ("↗", "#89b4fa"),        # search / web icon
        "system": ("⚙", "#a6e3a1"),
    }
    icon, color = meta.get(server, ("●", "#cdd6f4"))
    return icon, color


def format_tool_summary(tool_name: str, raw_output: str) -> str:
    """Format raw tool JSON or string output into a clean, concise single-line human summary."""
    if not raw_output:
        return "Executed successfully"

    clean_raw = raw_output.strip()

    # Specialized tool summary handlers
    if tool_name in ("read_file", "read_resource", "read_file_lines"):
        lines = [l for l in clean_raw.splitlines() if l.strip()]
        line_count = len(lines)
        size_bytes = len(clean_raw)
        size_str = f"{round(size_bytes / 1024, 1)} KB" if size_bytes > 1024 else f"{size_bytes} bytes"
        # Get first meaningful line (skip braces/brackets)
        first_text = ""
        for l in lines:
            stripped = l.strip().strip("{}[]\"',")
            if stripped and len(stripped) > 3:
                first_text = stripped[:50]
                break
        return f"Read {size_str} ({line_count} lines)" + (f" — '{first_text}'" if first_text else "")

    if tool_name in ("write_file", "append_file", "replace_file_content"):
        return "File updated successfully"

    if tool_name in ("run_shell", "execute_command", "run_command"):
        try:
            data = json.loads(clean_raw)
            if isinstance(data, dict):
                exit_code = data.get("exit_code", 0)
                stdout = (data.get("stdout") or "").strip()
                stderr = (data.get("stderr") or "").strip()
                if exit_code == 0:
                    first_out = stdout.splitlines()[0][:60] if stdout else ""
                    return "Command exit 0" + (f" — '{first_out}'" if first_out else "")
                else:
                    return f"Command failed (exit {exit_code}): {stderr[:60]}"
        except Exception:
            pass

    # Try JSON parsing for structured outputs
    try:
        data = json.loads(clean_raw)

        # Handle list_directory — output is a list of file dicts
        if tool_name in ("list_directory",):
            if isinstance(data, list):
                dirs = sum(1 for x in data if isinstance(x, dict) and x.get("is_dir"))
                files = len(data) - dirs
                return f"Directory listed ({len(data)} items — {dirs} dirs, {files} files)"
            elif isinstance(data, dict):
                items = data.get("items", []) or data.get("result", []) or data.get("entries", [])
                if isinstance(items, list):
                    return f"Directory listed ({len(items)} items)"

        if tool_name in ("search_files", "find_files"):
            if isinstance(data, list):
                dirs = sum(1 for x in data if isinstance(x, dict) and x.get("is_dir"))
                files = len(data) - dirs
                return f"File search completed ({len(data)} matches — {files} files, {dirs} dirs)"

        if tool_name == "explore_directory":
            if isinstance(data, dict):
                name = data.get("name", "")
                dirs_count = len(data.get("directories", []))
                files_count = len(data.get("files", []))
                return f"Explored directory '{name}' ({dirs_count} subdirs, {files_count} files)"

        if tool_name in ("web_search", "web_search_and_read"):
            if isinstance(data, dict):
                results = data.get("results", []) or data.get("sources", [])
                query = data.get("query", "")
                count = len(results) if isinstance(results, list) else 0
                return f"Web search for '{query}' returned {count} sources"
            elif isinstance(data, list):
                return f"Web search returned {len(data)} results"

        if tool_name == "web_fetch":
            if isinstance(data, dict):
                title = data.get("title", "") or data.get("final_url", "") or data.get("url", "")
                chars = len(data.get("text", "") or data.get("content", ""))
                size_str = f"{round(chars / 1024, 1)} KB" if chars > 1024 else f"{chars} chars"
                return f"Web page fetched ({size_str})" + (f" — '{title[:50]}'" if title else "")

        if tool_name == "web_download_file":
            if isinstance(data, dict):
                fname = data.get("filename", "") or "file"
                size = data.get("size_human", "") or "downloaded"
                status = data.get("status", "")
                if status == "success":
                    return f"Downloaded '{fname}' ({size})"
                return f"Download failed for '{fname}': {data.get('message', '')}"

        if tool_name == "web_search_and_download":
            if isinstance(data, dict):
                downloads = data.get("downloads", [])
                query = data.get("query", "")
                count = len(downloads) if isinstance(downloads, list) else 0
                return f"Downloaded {count} files matching '{query}'"

        if isinstance(data, dict):
            if tool_name == "read_graph":
                entities = len(data.get("entities", []))
                relations = len(data.get("relations", []))
                return f"Memory graph queried ({entities} entities, {relations} relations)"
            if tool_name == "search_nodes":
                nodes = len(data.get("nodes", []))
                return f"Memory nodes searched ({nodes} results)"
            if tool_name == "create_entities":
                added = len(data.get("entities", []))
                return f"Created {added} memory entities"
            if tool_name == "add_observations":
                return "Added observations to memory graph"
            if tool_name == "get_system_status":
                cpu = data.get("cpu_percent", 0)
                mem = data.get("memory", {}).get("percent_used", 0)
                return f"System status fetched (CPU: {cpu}%, RAM: {mem}%)"
            if "message" in data:
                return str(data["message"])[:70]
            if "status" in data:
                return str(data["status"])[:70]
            # Generic dict — show key count
            return f"Returned {len(data)} fields"

        elif isinstance(data, list):
            return f"Retrieved {len(data)} items"
    except Exception:
        pass

    # Default: concise non-JSON summary — never show raw JSON chars
    lines = clean_raw.splitlines()
    for line in lines:
        stripped = line.strip()
        # Skip JSON syntax lines
        if stripped in ("{", "}", "[", "]", "") or stripped.startswith('"') and stripped.endswith('",'):
            continue
        # Skip lines that look like raw JSON fields
        if stripped.startswith('"') and '":' in stripped:
            continue
        clean = stripped.strip("{}[]\"',")
        if clean and len(clean) > 3:
            return clean[:70]

    return "Executed successfully"


class ToolExecutionCard:
    """Represents a single tool call execution inside a grouped step."""

    def __init__(
        self,
        server: str,
        tool_name: str,
        elapsed_sec: float,
        output_summary: str,
        success: bool = True,
    ):
        self.server = server
        self.tool_name = tool_name
        self.elapsed_sec = elapsed_sec
        self.output_summary = output_summary
        self.success = success

    def render_row(self) -> Table:
        icon, color = get_server_icon_color(self.server)
        table = Table.grid(expand=True)
        table.add_column()

        status_text = Text()
        if self.success:
            status_text.append("  ✓ ", style="bold #a6e3a1")
            status_text.append(self.output_summary, style="#cdd6f4")
        else:
            status_text.append("  ✗ ", style="bold #f38ba8")
            status_text.append(self.output_summary, style="#f38ba8")

        table.add_row(status_text)
        return table


class PhaseRenderer:
    """Renders structured agent execution phases (Understanding, Planning, Executing tools, Result)."""

    @staticmethod
    def render_phase(title: str, body: str, icon: str = "✦", color: str = "#89b4fa") -> Panel:
        header = Text()
        header.append(f"{icon} ", style=f"bold {color}")
        header.append(title, style=f"bold {color}")

        content = Text()
        content.append(body, style="#cdd6f4")

        outer = Table.grid(expand=True)
        outer.add_column()
        outer.add_row(header)
        outer.add_row(content)

        return Panel(
            outer,
            border_style="#45475a",
            box=ROUNDED,
            padding=(0, 1),
        )

    @staticmethod
    def render_grouped_tools(tools: List[ToolExecutionCard]) -> Panel:
        """Renders executed tool cards — header only (collapsed). Details shown on expand."""
        if not tools:
            return Panel(Text(""))

        tool_names = ", ".join(f"{t.server} › {t.tool_name}" for t in tools)
        total_time = sum(t.elapsed_sec for t in tools)
        time_str = f"{int(total_time * 1000)}ms" if total_time < 1.0 else f"{total_time:.3f}s"

        header_table = Table.grid(expand=True)
        header_table.add_column()
        header_table.add_column(justify="right")

        header_left = Text()
        header_left.append("⚙ ", style="bold #a6e3a1")
        header_left.append("Executing tools: ", style="bold #a6e3a1")
        header_left.append(tool_names, style="bold #89b4fa")

        header_table.add_row(header_left, Text(time_str, style="dim #a6adc8"))

        return Panel(
            header_table,
            border_style="#45475a",
            box=ROUNDED,
            padding=(0, 1),
        )

    @staticmethod
    def render_tool_details(tools: List[ToolExecutionCard]) -> Table:
        """Renders detail rows for tool cards (shown when expanded)."""
        table = Table.grid(expand=True, padding=(0, 0))
        table.add_column()

        for tool in tools:
            status_text = Text()
            if tool.success:
                status_text.append("  ✓ ", style="bold #a6e3a1")
                status_text.append(tool.output_summary, style="#cdd6f4")
            else:
                status_text.append("  ✗ ", style="bold #f38ba8")
                status_text.append(tool.output_summary, style="#f38ba8")
            table.add_row(status_text)

        return table
