from __future__ import annotations

import asyncio
import os
import sys
from contextlib import suppress
from datetime import datetime
from typing import List, Optional

from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from textual import events, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Input, RichLog, Static

from pihu.agent.orchestrator import PihuAgent
from pihu.mcp.manager import MCPManager
from pihu.config.settings import settings
from pihu.llm.base import Message
from pihu.ui.input import PihuCommandSuggester
from pihu.ui.renderer import TextualConsoleAdapter, PihuMarkdown
from pihu.ui.widgets import (
    SystemPanelWidget,
    MCPStatusPanelWidget,
    ShortcutPanelWidget,
    ActivityStatusWidget,
    PihuFooterWidget,
    SuggestionBoxWidget,
)
from pihu.ui.modals import ModelSelectModal, MCPListModal, ToolListModal, CommandPaletteModal

from textual.theme import Theme

transparent_theme = Theme(
    name="transparent",
    primary="#cba6f7",
    secondary="#89b4fa",
    warning="#f9e2af",
    error="#f38ba8",
    success="#a6e3a1",
    accent="#94e2d5",
    foreground="#cdd6f4",
    background="#1e1e2e",
    surface="#1e1e2e",
    panel="#181825",
    boost="#313244",
    dark=True,
)


class PihuApp(App):
    """PIHU Terminal IDE Agent TUI Application."""

    TITLE = "PIHU"
    SUB_TITLE = "Personalized Intelligent Human Utility"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("ctrl+l", "clear_screen", "Clear", show=False),
        Binding("ctrl+c", "cancel_task", "Cancel", show=False),
        Binding("ctrl+d", "quit", "Exit", show=False),
        Binding("ctrl+p", "open_palette", "Palette"),
    ]

    def __init__(
        self,
        initial_provider: str = "",
        initial_model: str = "",
    ):
        super().__init__()

        self.register_theme(transparent_theme)
        self.theme = "transparent"

        self.current_provider = initial_provider or settings.default_provider
        self.current_model = initial_model or (
            settings.gemini_model if self.current_provider == "gemini" else settings.ollama_model
        )
        self.offline_mode = False
        self.active_mcp_filter: Optional[str] = None

        self.mcp_manager = MCPManager()
        self.agent = PihuAgent(mcp_manager=self.mcp_manager)

        self.session_history: List[Message] = []
        self.server_count = 0
        self.tool_count = 0

    # ========================================================
    # LAYOUT COMPOSITION
    # ========================================================

    def compose(self) -> ComposeResult:
        with Horizontal(id="main-layout"):
            # Main conversation column
            with Vertical(id="conversation-column"):
                yield Static(self.header_status(), id="status-line")
                yield RichLog(
                    id="conversation",
                    markup=True,
                    highlight=True,
                    wrap=True,
                    auto_scroll=True,
                )
                yield SuggestionBoxWidget(id="suggestion-box")
                yield ActivityStatusWidget(id="activity-status")
                with Horizontal(id="input-row"):
                    yield Static("›", id="prompt-symbol")
                    yield Input(
                        placeholder="Ask PIHU anything...",
                        id="prompt",
                        suggester=PihuCommandSuggester(),
                    )

            # Right side panel
            with Vertical(id="side-panel"):
                yield SystemPanelWidget(id="system-panel")
                yield MCPStatusPanelWidget(id="mcp-panel")
                yield ShortcutPanelWidget(id="shortcut-panel")

        yield PihuFooterWidget(id="pihu-footer")

    def set_activity_status(self, message: str) -> None:
        try:
            widget = self.query_one("#activity-status", ActivityStatusWidget)
            widget.start_status(message)
        except Exception:
            pass

    def clear_activity_status(self) -> None:
        try:
            widget = self.query_one("#activity-status", ActivityStatusWidget)
            widget.stop_status()
        except Exception:
            pass

    # ========================================================
    # STARTUP & WORKERS
    # ========================================================

    def on_mount(self):
        self.run_mcp_initialization()
        self.update_footer()

    def update_footer(self):
        try:
            footer = self.query_one("#pihu-footer", PihuFooterWidget)
            footer.update_footer(f"{self.current_provider}:{self.current_model}", self.offline_mode)
        except Exception:
            pass

    @work(exclusive=True, group="mcp-init")
    async def run_mcp_initialization(self):
        try:
            tools = await self.mcp_manager.load_and_initialize()
            self.server_count = len(self.mcp_manager.sessions)
            self.tool_count = len(tools)

            # Dynamically update input autocompletions with real discovered tools & servers
            prompt_input = self.query_one("#prompt", Input)
            if hasattr(prompt_input, "suggester") and prompt_input.suggester:
                dynamic_cmds = []
                for tool in tools:
                    dynamic_cmds.append(f"/tools {tool.name}")
                for srv in self.mcp_manager.sessions.keys():
                    dynamic_cmds.append(f"/mcp {srv}")
                if hasattr(prompt_input.suggester, "add_commands"):
                    prompt_input.suggester.add_commands(dynamic_cmds)

            self.update_status()
            self.update_mcp_panel()
            self.show_welcome()
        except Exception as exc:
            self.show_error(f"MCP initialization failed: {exc}")

    # ========================================================
    # STATUS & PANELS
    # ========================================================

    def header_status(self) -> Table:
        table = Table.grid(expand=True)
        table.add_column()
        table.add_column(justify="right")

        left = Text()
        left.append("✦ PIHU", style="bold #cba6f7")

        st = Text()
        if self.offline_mode:
            st.append("● OFFLINE", style="bold #f9e2af")
        else:
            st.append("● ONLINE", style="bold #a6e3a1")

        table.add_row(left, st)
        return table

    def update_status(self):
        self.query_one("#status-line", Static).update(self.header_status())
        self.update_footer()

    def update_mcp_panel(self):
        mcp_widget = self.query_one("#mcp-panel", MCPStatusPanelWidget)
        mcp_widget.update_mcp_status(self.mcp_manager)

    # ========================================================
    # WELCOME & MESSAGES
    # ========================================================

    def show_welcome(self):
        log = self.query_one("#conversation", RichLog)

        ascii_lines = [
            "██████╗ ██╗██╗  ██╗██╗  ██╗",
            "██╔══██╗██║██║  ██║██║  ██║",
            "██████╔╝██║███████║██║  ██║",
            "██╔═══╝ ██║██╔══██║██║  ██║",
            "██║     ██║██║  ██║╚█████╔╝",
            "╚═╝     ╚═╝╚═╝  ╚═╝ ╚════╝",
        ]

        grid = Table.grid(expand=True)
        grid.add_column(justify="center")

        for line in ascii_lines:
            grid.add_row(Text(line, style="bold #cba6f7"))

        grid.add_row(Text(""))
        grid.add_row(Text("Personalized Intelligent Human Utility", style="italic #89b4fa"))
        grid.add_row(Text(""))

        status_text = Text()
        status_text.append("Ready. ", style="bold #a6e3a1")
        status_text.append("Ask me anything or type ", style="dim #a6adc8")
        status_text.append("/help", style="bold #cba6f7")
        status_text.append(" for commands.", style="dim #a6adc8")
        grid.add_row(status_text)

        log.write(
            Panel(
                grid,
                border_style="#45475a",
                padding=(1, 2),
            )
        )

    def on_key(self, event: events.Key) -> None:
        try:
            box = self.query_one("#suggestion-box", SuggestionBoxWidget)
            prompt_input = self.query_one("#prompt", Input)
            log = self.query_one("#conversation", RichLog)
        except Exception:
            return

        key_name = event.key

        # 1. Handle suggestion box navigation if visible
        if box.styles.display != "none":
            k_lower = key_name.lower()
            if k_lower in ("down", "ctrl+j", "ctrl+n") or (k_lower == "j" and not prompt_input.value):
                box.move_cursor_down()
                event.prevent_default()
                event.stop()
                return
            elif k_lower in ("up", "ctrl+k", "ctrl+p") or (k_lower == "k" and not prompt_input.value):
                box.move_cursor_up()
                event.prevent_default()
                event.stop()
                return
            elif k_lower in ("enter", "tab"):
                box.select_highlighted()
                event.prevent_default()
                event.stop()
                return
            elif k_lower == "escape":
                box.hide()
                event.prevent_default()
                event.stop()
                return

        # 2. Escape key in insert mode: exit to normal mode
        if key_name.lower() == "escape":
            if prompt_input.has_focus:
                prompt_input.blur()
                event.prevent_default()
                event.stop()
                return

        # 3. Vim Normal mode navigation (when input is not focused)
        if not prompt_input.has_focus:
            if key_name == "i":
                prompt_input.focus()
                event.prevent_default()
                event.stop()
                return
            elif key_name == "slash":
                prompt_input.focus()
                prompt_input.value = "/"
                event.prevent_default()
                event.stop()
                return
            elif key_name in ("j", "down"):
                log.scroll_down(animate=False)
                event.prevent_default()
                event.stop()
                return
            elif key_name in ("k", "up"):
                log.scroll_up(animate=False)
                event.prevent_default()
                event.stop()
                return
            elif key_name == "g":
                log.scroll_home(animate=False)
                event.prevent_default()
                event.stop()
                return
            elif key_name == "G":
                log.scroll_end(animate=False)
                event.prevent_default()
                event.stop()
                return

    def on_input_changed(self, event: Input.Changed):
        val = event.value
        box = self.query_one("#suggestion-box", SuggestionBoxWidget)

        if not val:
            if not getattr(self, "_active_modal_open", False):
                box.hide()
            return

        self._active_modal_open = False

        # 1. Path & File Explorer for @file
        if "@" in val:
            at_idx = val.rfind("@")
            query = val[at_idx + 1:]

            # If space/newline after @file token, token completion is finished -> hide suggestion box!
            if " " in query or "\n" in query or (not query and val.endswith(" ")):
                if not val.startswith("/"):
                    box.hide()
            else:
                suggestions = self._resolve_path_suggestions(query, dirs_only=False)
                options = [(s[0], s[1]) for s in suggestions]

                if options:
                    def on_file_selected(selected_path: str):
                        prompt_input = self.query_one("#prompt", Input)
                        cur_val = prompt_input.value
                        at_pos = cur_val.rfind("@")
                        if at_pos != -1:
                            suffix = "" if selected_path.endswith("/") else " "
                            new_val = cur_val[:at_pos] + "@" + selected_path + suffix
                            prompt_input.value = new_val
                            prompt_input.focus()
                        box.hide()

                    box.show_suggestions("✦ File & Directory Explorer (@file)", options, on_file_selected)
                    return

        # 2. Path & Directory Search for /cd <query>
        if val.startswith("/cd ") or val == "/cd":
            query = val[3:].strip()
            suggestions = self._resolve_path_suggestions(query, dirs_only=True)
            options = [(s[0], s[1]) for s in suggestions]

            if options:
                def on_cd_selected(selected_path: str):
                    prompt_input = self.query_one("#prompt", Input)
                    prompt_input.value = f"/cd {selected_path}"
                    prompt_input.focus()

                box.show_suggestions("✦ Directory Explorer (/cd)", options, on_cd_selected)
                return

        # 3. Fuzzy MCP Search for /mcp <query> and /tools <query>
        if val.startswith("/mcp ") or val.startswith("/tools "):
            is_tools = val.startswith("/tools ")
            query = val[7:].strip() if is_tools else val[5:].strip()

            if is_tools:
                candidates = list(self.mcp_manager.tool_map.keys())
            else:
                candidates = list(self.mcp_manager.sessions.keys())

            import difflib
            q_lower = query.lower()
            scored = []
            for cand in candidates:
                c_lower = cand.lower()
                if not q_lower:
                    score = 100
                elif q_lower in c_lower:
                    score = 100 - c_lower.find(q_lower)
                else:
                    ratio = difflib.SequenceMatcher(None, q_lower, c_lower).ratio()
                    if ratio < 0.3:
                        continue
                    score = int(ratio * 70)
                scored.append((score, cand))

            scored.sort(key=lambda x: x[0], reverse=True)
            prefix_cmd = "/tools " if is_tools else "/mcp "
            options = [(c, f"⚙ {c}") for _, c in scored[:15]]

            if options:
                def on_mcp_selected(selected_item: str):
                    prompt_input = self.query_one("#prompt", Input)
                    prompt_input.value = f"{prefix_cmd}{selected_item}"
                    prompt_input.focus()

                box.show_suggestions("✦ MCP Search", options, on_mcp_selected)
                return

        if not val.startswith("/"):
            box.hide()

    def _resolve_path_suggestions(self, query: str, dirs_only: bool = False) -> List[Tuple[str, str, bool]]:
        raw = query.strip().lstrip("@")
        import difflib

        if raw.startswith("~"):
            expanded = os.path.expanduser(raw)
            if raw in ("~", "~/"):
                search_dir = os.path.expanduser("~")
                filter_str = ""
                display_prefix = "~/"
            elif raw.endswith("/"):
                search_dir = expanded
                filter_str = ""
                display_prefix = raw
            else:
                search_dir = os.path.dirname(expanded) or os.path.expanduser("~")
                filter_str = os.path.basename(raw)
                parent = os.path.dirname(raw)
                display_prefix = (parent + "/") if parent else "~/"
        elif raw.startswith("/") or "/" in raw or raw in (".", "..", "./", "../"):
            expanded = os.path.expanduser(raw)
            if raw.endswith("/") or raw in (".", "..", "./", "../"):
                search_dir = expanded
                filter_str = ""
                display_prefix = raw if raw.endswith("/") else (raw + "/")
            else:
                search_dir = os.path.dirname(expanded) or "."
                filter_str = os.path.basename(raw)
                parent = os.path.dirname(raw)
                display_prefix = (parent + "/") if parent else ""
        else:
            search_dir = "."
            filter_str = raw
            display_prefix = ""

        search_dir_abs = os.path.abspath(search_dir)
        results = []

        if os.path.isdir(search_dir_abs):
            try:
                entries = sorted(os.listdir(search_dir_abs))
            except Exception:
                entries = []

            q_lower = filter_str.lower()

            if not raw and dirs_only:
                results.append((110, "~/", "◫ ~/", True))
                results.append((105, "../", "◫ ../", True))

            for entry in entries:
                full_path = os.path.join(search_dir_abs, entry)
                is_dir = os.path.isdir(full_path)
                if dirs_only and not is_dir:
                    continue

                suffixed_entry = entry + ("/" if is_dir else "")
                insert_val = display_prefix + suffixed_entry
                icon = "◫" if is_dir else "›"
                label = f"{icon} {insert_val}"

                if not q_lower:
                    score = 100 if is_dir else 50
                elif q_lower in entry.lower():
                    score = 100 - entry.lower().find(q_lower)
                else:
                    ratio = difflib.SequenceMatcher(None, q_lower, entry.lower()).ratio()
                    if ratio < 0.35:
                        continue
                    score = int(ratio * 70)

                results.append((score, insert_val, label, is_dir))

        if filter_str and not "/" in raw and not raw.startswith("~"):
            ignore = {".git", ".venv", "node_modules", "__pycache__", ".trash", ".idea", ".vscode"}
            for root, dirs, files in os.walk("."):
                dirs[:] = [d for d in dirs if d not in ignore]
                for d in dirs:
                    rel = os.path.relpath(os.path.join(root, d), ".") + "/"
                    if rel in [r[1] for r in results]:
                        continue
                    d_lower = d.lower()
                    if q_lower in d_lower:
                        results.append((90 - d_lower.find(q_lower), rel, f"◫ {rel}", True))
                if not dirs_only:
                    for f in files:
                        rel = os.path.relpath(os.path.join(root, f), ".")
                        if rel in [r[1] for r in results]:
                            continue
                        f_lower = f.lower()
                        if q_lower in f_lower:
                            results.append((80 - f_lower.find(q_lower), rel, f"› {rel}", False))

        results.sort(key=lambda x: x[0], reverse=True)
        seen = set()
        final_list = []
        for item in results:
            val_name = item[1]
            if val_name not in seen:
                seen.add(val_name)
                final_list.append((val_name, item[2], item[3]))

        return final_list[:15]

    # ========================================================
    # INPUT SUBMISSION
    # ========================================================

    async def on_input_submitted(self, event: Input.Submitted):
        value = event.value.strip()
        if not value:
            return

        event.input.value = ""
        log = self.query_one("#conversation", RichLog)

        # Print user query with highlighted @file tokens
        user = Text()
        user.append("\nYou ", style="bold #89b4fa")
        user.append("› ", style="dim")

        import re
        tokens = re.split(r'(@[\w\.\/\-]+)', value)
        for t in tokens:
            if t.startswith("@"):
                user.append(t, style="bold #cba6f7")
            else:
                user.append(t, style="bold white")

        log.write(user)

        # Handle slash commands
        if value.startswith("/"):
            await self.handle_command(value)
            return

        # Agent task execution
        self.session_history.append(Message(role="user", content=value))
        self.run_agent(value)

    # ========================================================
    # AGENT WORKER
    # ========================================================

    @work(exclusive=True, group="agent-task")
    async def run_agent(self, prompt: str, target_server: Optional[str] = None):
        log = self.query_one("#conversation", RichLog)
        adapter = TextualConsoleAdapter(log)
        start = datetime.now()

        effective_server = target_server or self.active_mcp_filter

        try:
            await self.agent.run_task_interactive(
                prompt=prompt,
                console=adapter,
                history=self.session_history,
                preferred_provider=self.current_provider,
                preferred_model=self.current_model,
                target_server=effective_server,
            )
            elapsed = (datetime.now() - start).total_seconds()
            log.write(Text(f"  ✓ completed in {elapsed:.2f}s\n", style="#a6e3a1"))
        except asyncio.CancelledError:
            log.write(Text("  ⚠ task cancelled\n", style="#f9e2af"))
        except Exception as exc:
            self.show_error(str(exc))

    # ========================================================
    # SLASH COMMAND HANDLER
    # ========================================================

    async def handle_command(self, command: str):
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        argument = parts[1] if len(parts) > 1 else ""

        if cmd in {"/exit", "/quit"}:
            self.exit()
            return

        if cmd == "/clear":
            self.query_one("#conversation", RichLog).clear()
            return

        if cmd == "/cd":
            box = self.query_one("#suggestion-box", SuggestionBoxWidget)
            box.hide()
            target_dir = argument.strip()
            if not target_dir:
                target_dir = "~"

            expanded_dir = os.path.expanduser(target_dir)
            if not os.path.isdir(expanded_dir):
                self.show_error(f"Directory does not exist: {target_dir}")
                return

            try:
                os.chdir(expanded_dir)
                self.update_status()
                log = self.query_one("#conversation", RichLog)

                entries = sorted(os.listdir(expanded_dir))
                dirs = [e + "/" for e in entries if os.path.isdir(os.path.join(expanded_dir, e))]
                files = [e for e in entries if os.path.isfile(os.path.join(expanded_dir, e))]

                md_lines = [
                    f"### ✦ Changed Working Directory to `{expanded_dir}`\n",
                    f"**Total items:** {len(entries)} ({len(dirs)} directories, {len(files)} files)\n",
                ]
                if dirs:
                    md_lines.append("**Directories:** " + ", ".join([f"`{d}`" for d in dirs[:25]]))
                if files:
                    md_lines.append("**Files:** " + ", ".join([f"`{f}`" for f in files[:35]]))

                log.write(PihuMarkdown("\n".join(md_lines)))

                from pihu.memory.db import db_engine
                await db_engine.record_activity("CHANGE_DIRECTORY", expanded_dir)
                await db_engine.index_project(os.path.basename(expanded_dir), expanded_dir)
            except Exception as e:
                self.show_error(f"Failed to change directory to {target_dir}: {e}")
            return

        if cmd == "/help":
            self.show_help()
            return

        if cmd in {"/palette", "/cmd"}:
            self.action_open_palette()
            return

        if cmd == "/provider":
            if argument and argument.lower().startswith("key"):
                key_arg = argument[3:].strip()
                await self.key_command(key_arg)
                return
            self.switch_provider()
            return

        if cmd in {"/key", "/keys"}:
            await self.key_command(argument)
            return

        if cmd in {"/config", "/configure"}:
            await self.web_search_config_command(argument)
            return

        if cmd in {"/mcp", "/servers"}:
            self.update_mcp_panel()
            if argument:
                arg_parts = argument.split(maxsplit=1)
                target_srv = arg_parts[0]
                task_prompt = arg_parts[1] if len(arg_parts) > 1 else ""

                if target_srv in self.mcp_manager.sessions:
                    self.active_mcp_filter = target_srv
                    self.query_one("#conversation", RichLog).write(
                        Text(f"✓ Focused MCP server: {target_srv}\n", style="#a6e3a1")
                    )
                    if task_prompt:
                        self.session_history.append(Message(role="user", content=task_prompt))
                        self.run_agent(task_prompt, target_server=target_srv)
                    return
                else:
                    self.show_error(f"Unknown MCP server: '{target_srv}'. Available: {list(self.mcp_manager.sessions.keys())}")
                    return

            # Print full MCP server status table directly to conversation log
            md_lines = ["### ✦ Connected MCP Servers\n", "| Status | Server | Tools |", "|---|---|---|"]
            for srv in sorted(self.mcp_manager.sessions.keys()):
                session = self.mcp_manager.sessions[srv]
                st_str = "● ONLINE" if session.session else "○ OFFLINE"
                t_count = sum(1 for t in self.mcp_manager.tools if t.name in self.mcp_manager.tool_map and self.mcp_manager.tool_map[t.name][0] == srv)
                md_lines.append(f"| `{st_str}` | **{srv}** | {t_count} tools |")

            self.query_one("#conversation", RichLog).write(PihuMarkdown("\n".join(md_lines)))

            box = self.query_one("#suggestion-box", SuggestionBoxWidget)
            options = []
            for srv in sorted(self.mcp_manager.sessions.keys()):
                session = self.mcp_manager.sessions[srv]
                status = "● " if session.session else "○ "
                tool_count = sum(1 for t in self.mcp_manager.tools if t.name in self.mcp_manager.tool_map and self.mcp_manager.tool_map[t.name][0] == srv)
                options.append((srv, f"{status}{srv}  ({tool_count} tools)"))

            def on_mcp_selected(srv_name: str):
                if srv_name:
                    self.active_mcp_filter = srv_name
                    self.query_one("#conversation", RichLog).write(
                        Text(f"✓ Focused MCP server: {srv_name}\n", style="#a6e3a1")
                    )

            box.show_suggestions("✦ MCP Servers", options, on_mcp_selected)
            return

        if cmd == "/tools":
            # Print full Tools Catalog directly to conversation log
            md_lines = ["### ✦ MCP Tools Catalog\n", "| Tool | Server | Description |", "|---|---|---|"]
            for tool in sorted(self.mcp_manager.tools, key=lambda t: t.name):
                srv = self.mcp_manager.tool_map.get(tool.name, ("?",))[0]
                desc = (tool.description or "No description")[:60]
                md_lines.append(f"| `{tool.name}` | `{srv}` | {desc} |")

            self.query_one("#conversation", RichLog).write(PihuMarkdown("\n".join(md_lines)))

            box = self.query_one("#suggestion-box", SuggestionBoxWidget)
            options = []
            for tool in sorted(self.mcp_manager.tools, key=lambda t: t.name):
                srv = self.mcp_manager.tool_map.get(tool.name, ("?",))[0]
                desc = (tool.description or "")[:50]
                options.append((tool.name, f"{tool.name}  [{srv}] {desc}"))

            def on_tool_selected(tool_name: str):
                if tool_name:
                    self.query_one("#conversation", RichLog).write(
                        Text(f"Tool: {tool_name}\n", style="#89b4fa")
                    )

            box.show_suggestions("✦ MCP Tools", options, on_tool_selected)
            return

        if cmd == "/offline":
            self.toggle_offline()
            return

        if cmd == "/model":
            await self.model_command(argument)
            return

        self.show_error(f"Unknown command: {cmd}")

    async def key_command(self, argument: str):
        import os
        from pathlib import Path

        def export_env_key(key_name: str, key_val: str) -> str:
            os.environ[key_name] = key_val

            env_paths = [Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"]
            target_env = env_paths[0]
            for p in env_paths:
                if p.exists():
                    target_env = p
                    break

            existing_lines = []
            if target_env.exists():
                existing_lines = target_env.read_text(encoding="utf-8").splitlines()

            updated = False
            new_lines = []
            for line in existing_lines:
                raw = line.strip()
                if raw and not raw.startswith("#") and "=" in raw:
                    k = raw.split("=", 1)[0].replace("export ", "").strip()
                    if k == key_name:
                        new_lines.append(f"{key_name}={key_val}")
                        updated = True
                        continue
                new_lines.append(line)

            if not updated:
                new_lines.append(f"{key_name}={key_val}")

            target_env.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            return str(target_env)

        def discover_keys() -> dict[str, str]:
            discovered: dict[str, str] = {}
            env_paths = [Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"]
            for p in env_paths:
                if p.exists():
                    try:
                        for line in p.read_text(encoding="utf-8").splitlines():
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                k, v = line.split("=", 1)
                                k = k.replace("export ", "").strip()
                                v = v.strip().strip("'\"")
                                if k.startswith("PIHU_") or k.endswith("_API_KEY") or k.endswith("_KEY"):
                                    discovered[k] = v
                    except Exception:
                        pass

            for k, v in os.environ.items():
                if (k.startswith("PIHU_") or k.endswith("_API_KEY") or k.endswith("_KEY")) and v:
                    discovered[k] = v

            for default_var in ("PIHU_GEMINI_API_KEY", "PIHU_OPENAI_API_KEY", "PIHU_ANTHROPIC_API_KEY"):
                if default_var not in discovered:
                    legacy = default_var.replace("PIHU_", "")
                    discovered[default_var] = discovered.get(legacy, os.getenv(legacy, ""))

            return discovered

        all_keys = discover_keys()

        def mask_key(k: str) -> str:
            if not k:
                return "Not set"
            return k[:6] + "..." + k[-4:] if len(k) > 10 else "****"

        if argument:
            parts = argument.strip().split(maxsplit=1)
            cmd_action = parts[0].lower()

            if cmd_action in ("use", "select", "switch") and len(parts) > 1:
                target_var = parts[1].strip()
                val = all_keys.get(target_var) or os.getenv(target_var, "")
                if not val:
                    self.show_error(f"Variable '{target_var}' has no key set.")
                    return

                if "GEMINI" in target_var:
                    settings.gemini_api_key = val
                    os.environ["GEMINI_API_KEY"] = val
                    os.environ["PIHU_GEMINI_API_KEY"] = val

                self.update_status()
                self.query_one("#conversation", RichLog).write(
                    Text(f"✓ Switched active key to {target_var} ({mask_key(val)})\n", style="#a6e3a1")
                )
                return

            var_name = parts[0]
            if not var_name.startswith("PIHU_") and "_" not in var_name:
                var_name = f"PIHU_{var_name.upper()}_API_KEY"

            if len(parts) > 1:
                val = parts[1].strip()
                env_file = export_env_key(var_name, val)

                if "GEMINI" in var_name:
                    settings.gemini_api_key = val
                    os.environ["GEMINI_API_KEY"] = val

                self.update_status()
                self.query_one("#conversation", RichLog).write(
                    Text(f"✓ Saved {var_name}={mask_key(val)} and exported to {env_file}\n", style="#a6e3a1")
                )
                return
            else:
                prompt_input = self.query_one("#prompt", Input)
                prompt_input.value = f"/key {var_name} "
                prompt_input.focus()
                return

        md_lines = [
            "### ✦ Dynamic API Key Manager\n",
            "| Variable Name | Provider | Current Status |",
            "|---|---|---|",
        ]

        for k in sorted(all_keys.keys()):
            val = all_keys[k]
            provider = k.replace("PIHU_", "").split("_")[0].title()
            md_lines.append(f"| `{k}` | **{provider}** | `{mask_key(val)}` |")

        md_lines.extend([
            "\n**Usage:**",
            "- Set/Export key: `/key PIHU_<PROVIDER>_<KEYNAME> <YOUR_KEY>`",
            "- Switch active key: Select from dropdown below or type `/key use <VAR_NAME>`",
        ])

        self.query_one("#conversation", RichLog).write(PihuMarkdown("\n".join(md_lines)))

        box = self.query_one("#suggestion-box", SuggestionBoxWidget)
        options = []
        for k in sorted(all_keys.keys()):
            val = all_keys[k]
            options.append((f"use:{k}", f"✦ Use {k}  ({mask_key(val)})"))
        options.append(("add_key", "+ Set / Export New API Key (PIHU_<PROVIDER>_<KEYNAME>)"))

        def on_key_selected(selected_id: str):
            prompt_input = self.query_one("#prompt", Input)
            if selected_id.startswith("use:"):
                var_name = selected_id[len("use:"):]
                val = all_keys.get(var_name, "")
                if val:
                    os.environ[var_name] = val
                    if "GEMINI" in var_name:
                        settings.gemini_api_key = val
                        os.environ["GEMINI_API_KEY"] = val
                        os.environ["PIHU_GEMINI_API_KEY"] = val
                    self.update_status()
                    self.query_one("#conversation", RichLog).write(
                        Text(f"✓ Switched active key to {var_name} ({mask_key(val)})\n", style="#a6e3a1")
                    )
                else:
                    prompt_input.value = f"/key {var_name} "
                    prompt_input.focus()
            elif selected_id == "add_key":
                prompt_input.value = "/key PIHU_GEMINI_API_KEY "
                prompt_input.focus()

        self._active_modal_open = True
        box.show_suggestions("✦ Dynamic API Key Manager", options, on_key_selected)

    async def web_search_config_command(self, argument: str = ""):
        current_brave_key = (
            os.getenv("PIHU_WEB_SEARCH_API_KEY")
            or os.getenv("PIHU_BRAVE_SEARCH_API_KEY")
            or os.getenv("BRAVE_SEARCH_API_KEY")
            or ""
        )
        masked = mask_key(current_brave_key) if current_brave_key else "Not Set (DuckDuckGo Free Fallback Active)"
        current_provider = os.getenv("WEB_SEARCH_PROVIDER", "brave" if current_brave_key else "duckduckgo")
        current_max = os.getenv("WEB_SEARCH_MAX_RESULTS", "8")

        md_lines = [
            "### ✦ Web Search MCP Configuration (`web-search`)\n",
            "| Setting | Environment Variable | Current Value |",
            "|---|---|---|",
            f"| **Brave API Key** | `PIHU_WEB_SEARCH_API_KEY` | `{masked}` |",
            f"| **Search Provider** | `WEB_SEARCH_PROVIDER` | `{current_provider}` |",
            f"| **Max Results** | `WEB_SEARCH_MAX_RESULTS` | `{current_max}` |",
            "\n**Usage:**",
            "- Set API key: `/key PIHU_WEB_SEARCH_API_KEY <YOUR_KEY>` or select option below",
            "- Set provider: Select option below or set `WEB_SEARCH_PROVIDER`",
        ]
        self.query_one("#conversation", RichLog).write(PihuMarkdown("\n".join(md_lines)))

        box = self.query_one("#suggestion-box", SuggestionBoxWidget)
        options = [
            ("set_key", "+ Set / Update Web Search API Key (PIHU_WEB_SEARCH_API_KEY)"),
            ("provider_brave", "✦ Set Provider: Brave Search (requires API key)"),
            ("provider_ddg", "✦ Set Provider: DuckDuckGo (free fallback, no API key needed)"),
        ]

        def on_selected(opt_id: str):
            prompt_input = self.query_one("#prompt", Input)
            if opt_id == "set_key":
                prompt_input.value = "/key PIHU_WEB_SEARCH_API_KEY "
                prompt_input.focus()
            elif opt_id == "provider_brave":
                os.environ["WEB_SEARCH_PROVIDER"] = "brave"
                self.query_one("#conversation", RichLog).write(
                    Text("✓ Search provider set to Brave Search\n", style="#a6e3a1")
                )
            elif opt_id == "provider_ddg":
                os.environ["WEB_SEARCH_PROVIDER"] = "duckduckgo"
                self.query_one("#conversation", RichLog).write(
                    Text("✓ Search provider set to DuckDuckGo (free fallback)\n", style="#a6e3a1")
                )

        self._active_modal_open = True
        box.show_suggestions("✦ Configure Web Search MCP", options, on_selected)

    def action_open_palette(self):
        box = self.query_one("#suggestion-box", SuggestionBoxWidget)
        cmds = [
            ("/model", "/model  › Switch LLM model"),
            ("/mcp", "/mcp  › View connected MCP servers"),
            ("/tools", "/tools  › Open MCP Tool Catalog"),
            ("/provider", "/provider  › Toggle Ollama / Gemini"),
            ("/offline", "/offline  › Toggle offline mode"),
            ("/clear", "/clear  › Clear conversation screen"),
            ("/help", "/help  › Show command reference guide"),
            ("/exit", "/exit  › Quit PIHU application"),
        ]

        def on_selected(cmd: str):
            if cmd:
                asyncio.create_task(self.handle_command(cmd))

        box.show_suggestions("✦ Command Palette", cmds, on_selected)

    def show_help(self):
        markdown = PihuMarkdown(
            """
### ✦ PIHU Commands

| Command | Description |
|---|---|
| `/help` | Show command reference guide |
| `/palette` | Open interactive Command Palette |
| `/tools` | Open interactive MCP tool catalog |
| `/mcp <name>` | Focus specific MCP server or view list |
| `/model` | Open interactive LLM model selector |
| `/provider` | Toggle between local Ollama and cloud Gemini |
| `/offline` | Toggle offline mode (Ollama local only) |
| `/clear` | Clear screen log |
| `/exit` | Exit PIHU |

### Keyboard Shortcuts
- `Ctrl+P` — Open Command Palette
- `Ctrl+L` — Clear screen
- `Ctrl+C` — Cancel task execution
- `Ctrl+D` — Exit
- `Right Arrow` — Accept command autocomplete suggestion
"""
        )
        self.query_one("#conversation", RichLog).write(markdown)

    def switch_provider(self):
        if self.offline_mode:
            self.show_error("Offline mode only allows local Ollama models.")
            return

        if self.current_provider == "ollama":
            self.current_provider = "gemini"
            self.current_model = settings.gemini_model
        else:
            self.current_provider = "ollama"
            self.current_model = settings.ollama_model

        self.update_status()
        self.query_one("#conversation", RichLog).write(
            Text(f"✓ Switched to {self.current_provider}:{self.current_model}\n", style="#a6e3a1")
        )

    def toggle_offline(self):
        self.offline_mode = not self.offline_mode
        if self.offline_mode:
            self.current_provider = "ollama"
            self.current_model = settings.ollama_model
            msg = "Offline mode ENABLED — using local Ollama models only."
        else:
            msg = "Online mode ENABLED — cloud models available."

        self.update_status()
        self.query_one("#conversation", RichLog).write(
            Text(f"⚡ {msg}\n", style="#f9e2af" if self.offline_mode else "#a6e3a1")
        )

    async def model_command(self, argument: str):
        if argument:
            arg_lower = argument.lower()
            if argument.startswith("gemini:"):
                self.current_provider = "gemini"
                self.current_model = argument[len("gemini:"):]
            elif argument.startswith("ollama:"):
                self.current_provider = "ollama"
                self.current_model = argument[len("ollama:"):]
            elif "gemini" in arg_lower:
                self.current_provider = "gemini"
                self.current_model = argument
            else:
                self.current_provider = "ollama"
                self.current_model = argument

            self.update_status()
            self.query_one("#conversation", RichLog).write(
                Text(f"✓ Model switched to {self.current_provider}:{self.current_model}\n", style="#a6e3a1")
            )
            return

        box = self.query_one("#suggestion-box", SuggestionBoxWidget)
        box.show_suggestions(
            "✦ Loading Available Models...",
            [("loading", "Fetching available models from Ollama & Gemini API...")],
            lambda x: None
        )

        from pihu.llm.ollama import OllamaProvider
        from pihu.llm.gemini import GeminiProvider

        ollama_prov = OllamaProvider()
        gemini_prov = GeminiProvider()

        try:
            ollama_models = await ollama_prov.list_models()
        except Exception:
            ollama_models = []

        try:
            gemini_models = await gemini_prov.list_models()
        except Exception:
            gemini_models = []

        options = []

        if gemini_models:
            for m in gemini_models:
                m_name = m.get("name", "")
                m_desc = m.get("description", m_name)
                options.append((f"gemini:{m_name}", f"[gemini] {m_name}  ({m_desc})"))
        else:
            options.append(("gemini:gemini-3.6-flash", "[gemini] gemini-3.6-flash (Cloud Default)"))
            options.append(("gemini:gemini-1.5-flash", "[gemini] gemini-1.5-flash (Cloud)"))

        if ollama_models:
            for m in ollama_models:
                m_name = m.get("name", "")
                param = m.get("parameter_size", "")
                size_gb = m.get("size_gb", 0)
                meta = f"{param}, {size_gb}GB" if param and size_gb else "Local"
                options.append((f"ollama:{m_name}", f"[ollama] {m_name}  ({meta})"))
        else:
            options.append(("ollama:qwen3:4b", "[ollama] qwen3:4b (Ollama Local Default)"))
            options.append(("ollama:gemma3:4b", "[ollama] gemma3:4b (Ollama Local)"))

        def on_model_selected(selected_id: str):
            if selected_id == "loading":
                return
            if ":" in selected_id:
                provider, model = selected_id.split(":", 1)
                self.current_provider = provider
                self.current_model = model
                self.update_status()
                self.query_one("#conversation", RichLog).write(
                    Text(f"✓ Model switched to {self.current_provider}:{self.current_model}\n", style="#a6e3a1")
                )

        box.show_suggestions("✦ Select LLM Model (Dynamic)", options, on_model_selected)

    def action_clear_screen(self):
        self.query_one("#conversation", RichLog).clear()

    def action_focus_prompt(self):
        self.query_one("#prompt", Input).focus()

    def action_cancel_task(self):
        self.show_error("Task cancellation requested.")

    def show_error(self, message: str):
        self.query_one("#conversation", RichLog).write(
            Panel(Text(message, style="#f38ba8"), title="[bold #f38ba8]Error[/]", border_style="#f38ba8")
        )


def run_tui(
    provider: str = "",
    model: str = "",
    initial_provider: str = "",
    initial_model: str = "",
):
    app = PihuApp(
        initial_provider=provider or initial_provider,
        initial_model=model or initial_model,
    )
    app.run()
