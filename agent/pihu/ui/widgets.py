from __future__ import annotations

import sys
import platform
import psutil
from typing import Dict, Any, List, Tuple, Callable, Optional
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static, OptionList, Label
from textual.widgets.option_list import Option
from pihu.mcp.manager import MCPManager


class SuggestionBoxWidget(Static):
    """Floating autocomplete suggestion box anchored right above the input bar."""

    DEFAULT_CSS = """
    SuggestionBoxWidget {
        display: none;
        height: auto;
        max-height: 18;
        width: 100%;
        margin: 0 1 0 1;
        background: #181825;
        border-top: round #7f5af0;
        border-left: round #7f5af0;
        border-right: round #7f5af0;
        border-bottom: none;
        padding: 0 1;
    }

    #suggestion-title {
        text-style: bold;
        color: #7f5af0;
        padding: 0 1;
        height: 1;
        background: #181825;
    }

    #suggestion-options {
        background: #181825;
        border: none;
        height: auto;
        max-height: 14;
        scrollbar-background: #181825;
        scrollbar-color: #585b70;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.callback: Optional[Callable[[str], None]] = None

    def compose(self) -> ComposeResult:
        yield Label("✦ Suggestions", id="suggestion-title")
        yield OptionList(id="suggestion-options")

    def show_suggestions(
        self,
        title: str,
        options: List[Tuple[str, str]],
        callback: Callable[[str], None],
    ) -> None:
        self.callback = callback
        title_widget = self.query_one("#suggestion-title", Label)
        title_widget.update(title)

        opt_list = self.query_one("#suggestion-options", OptionList)
        opt_list.clear_options()

        for value, label in options:
            opt_list.add_option(Option(label, id=value))

        if options:
            opt_list.highlighted = 0

        self.styles.display = "block"

        # Merge visually with input row: remove top border of input row
        try:
            input_row = self.app.query_one("#input-row")
            input_row.styles.border_top = ("", "transparent")
        except Exception:
            pass

    def move_cursor_down(self) -> None:
        opt_list = self.query_one("#suggestion-options", OptionList)
        if opt_list.option_count > 0:
            if opt_list.highlighted is None:
                opt_list.highlighted = 0
            else:
                opt_list.highlighted = min(opt_list.highlighted + 1, opt_list.option_count - 1)

    def move_cursor_up(self) -> None:
        opt_list = self.query_one("#suggestion-options", OptionList)
        if opt_list.option_count > 0:
            if opt_list.highlighted is None:
                opt_list.highlighted = 0
            else:
                opt_list.highlighted = max(opt_list.highlighted - 1, 0)

    def select_highlighted(self) -> None:
        opt_list = self.query_one("#suggestion-options", OptionList)
        if opt_list.option_count > 0:
            idx = opt_list.highlighted if opt_list.highlighted is not None else 0
            try:
                opt = opt_list.get_option_at_index(idx)
                val = str(opt.id)
                cb = self.callback
                self.hide()
                if cb:
                    cb(val)
            except Exception:
                self.hide()

    def hide(self) -> None:
        self.styles.display = "none"
        self.callback = None

        # Restore input row top border
        try:
            input_row = self.app.query_one("#input-row")
            input_row.styles.border_top = ("round", "#7f5af0")
        except Exception:
            pass

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        val = str(event.option.id)
        cb = self.callback
        self.hide()
        if cb:
            cb(val)


class PihuFooterWidget(Static):
    """Custom footer bar displaying PIHU version, active model, current working directory, GitHub link, and palette shortcut."""

    def update_footer(self, model_info: str, is_offline: bool) -> None:
        import os
        table = Table.grid(expand=True)
        table.add_column(style="bold #cba6f7")
        table.add_column(justify="center")
        table.add_column(justify="center")
        table.add_column(justify="center")
        table.add_column(justify="right")

        # Left: PIHU v0.1.0
        left = Text()
        left.append(" ✦ PIHU ", style="bold #cba6f7")
        left.append("v0.1.0", style="dim #a6adc8")

        # Model info (clean unicode icon instead of emoji)
        model_text = Text()
        model_text.append("✦ ", style="#f9e2af" if is_offline else "#a6e3a1")
        model_text.append(model_info, style="bold #89b4fa")

        # Current working directory
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        disp_cwd = ("~" + cwd[len(home):]) if cwd.startswith(home) else cwd

        cwd_text = Text()
        cwd_text.append("◫ ", style="bold #94e2d5")
        cwd_text.append(disp_cwd, style="dim #bac2de")

        # GitHub user
        gh_text = Text()
        gh_text.append("the-mayankjha", style="bold #94e2d5")

        # Right: Palette shortcut
        right = Text()
        right.append("^p ", style="bold #cba6f7")
        right.append("palette ", style="dim #a6adc8")

        table.add_row(left, model_text, cwd_text, gh_text, right)
        self.update(table)


class ActivityStatusWidget(Static):
    """Live animated status indicator widget for Thinking / Tool execution states."""

    SPINNER_FRAMES = ["◌", "◔", "◑", "◕", "●", "◕", "◑", "◔"]
    DOT_FRAMES = [".", ". .", ". . ."]

    def __init__(self, **kwargs):
        super().__init__("", **kwargs)
        self.current_message = ""
        self.frame_idx = 0
        self.timer = None
        self.styles.display = "none"

    def start_status(self, message: str) -> None:
        import re
        clean_msg = re.sub(r"\[.*?\]", "", message).strip()
        clean_msg = re.sub(r"^[◌⠋◐◓◑◒\s]+", "", clean_msg).strip()
        clean_msg = re.sub(r"\.+$", "", clean_msg).strip()
        self.current_message = clean_msg
        self.styles.display = "block"
        if not self.timer:
            self.timer = self.set_interval(0.2, self._update_frame)
        self._update_frame()
        try:
            if self.app:
                conv = self.app.query_one("#conversation")
                conv.scroll_end(animate=False)
        except Exception:
            pass

    def stop_status(self) -> None:
        if self.timer:
            self.timer.stop()
            self.timer = None
        self.current_message = ""
        self.styles.display = "none"
        self.update("")

    def _update_frame(self) -> None:
        if not self.current_message:
            self.styles.display = "none"
            self.update("")
            return
        spinner = self.SPINNER_FRAMES[self.frame_idx % len(self.SPINNER_FRAMES)]
        dots = self.DOT_FRAMES[(self.frame_idx // 2) % len(self.DOT_FRAMES)]
        self.frame_idx += 1
        text = Text()
        text.append(f"  {spinner} ", style="bold #7f849c")
        text.append(self.current_message, style="dim #a6adc8")
        text.append(f" {dots}", style="bold #7f849c")
        self.update(text)


class SystemPanelWidget(Static):
    """Widget displaying local system resources and hardware identity."""

    def on_mount(self) -> None:
        self.update_info()

    def update_info(self) -> None:
        try:
            mem = psutil.virtual_memory()
            cpu_pct = psutil.cpu_percent(interval=None)
            mem_used_gb = round(mem.used / (1024**3), 1)
            mem_total_gb = round(mem.total / (1024**3), 1)

            table = Table.grid(padding=(0, 1))
            table.add_column(style="#89b4fa")
            table.add_column(style="dim", justify="right")

            table.add_row("OS", platform.system())
            table.add_row("CPU Load", f"{cpu_pct}%")
            table.add_row("RAM Usage", f"{mem_used_gb}/{mem_total_gb} GB")
            table.add_row("Python", sys.version.split()[0])

            panel = Panel(
                table,
                title="[bold #cba6f7]System[/]",
                border_style="#45475a",
                padding=(0, 1),
            )
            self.update(panel)
        except Exception:
            pass


class MCPStatusPanelWidget(Static):
    """Widget displaying connected MCP servers and tool breakdown."""

    def update_mcp_status(self, mcp_manager: MCPManager) -> None:
        counts: Dict[str, int] = {}
        for tool in mcp_manager.tools:
            if tool.name in mcp_manager.tool_map:
                server = mcp_manager.tool_map[tool.name][0]
                counts[server] = counts.get(server, 0) + 1

        table = Table.grid(padding=(0, 1))
        table.add_column(style="#94e2d5")
        table.add_column(justify="right", style="dim")

        if not mcp_manager.sessions:
            table.add_row("Connecting...", "0")
        else:
            for server in sorted(mcp_manager.sessions.keys()):
                session = mcp_manager.sessions[server]
                row = Text()
                row.append("● ", style="#a6e3a1" if session.session else "#f38ba8")
                row.append(server)
                table.add_row(row, str(counts.get(server, 0)))

        panel = Panel(
            table,
            title="[bold #cba6f7]MCP Servers[/]",
            border_style="#45475a",
            padding=(0, 1),
        )
        self.update(panel)


class ShortcutPanelWidget(Static):
    """Widget displaying quick command cheatsheet."""

    def on_mount(self) -> None:
        content = Text.from_markup(
            "[bold #cba6f7]Commands[/]\n\n"
            "[#89b4fa]/help[/]       commands\n"
            "[#89b4fa]/tools[/]      MCP tools\n"
            "[#89b4fa]/mcp[/]        MCP servers\n"
            "[#89b4fa]/model[/]      switch model\n"
            "[#89b4fa]/provider[/]   switch provider\n"
            "[#89b4fa]/offline[/]    offline mode\n"
            "[#89b4fa]/clear[/]      clear screen\n"
            "[#89b4fa]/exit[/]       quit"
        )
        panel = Panel(
            content,
            border_style="#45475a",
            padding=(0, 1),
        )
        self.update(panel)
