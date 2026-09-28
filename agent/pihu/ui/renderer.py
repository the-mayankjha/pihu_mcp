from __future__ import annotations

import re
from typing import Any, List
from rich.console import Console, ConsoleOptions, RenderResult
from rich.markdown import CodeBlock, Markdown, TextElement, Token
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from textual.widgets import RichLog

from pihu.ui.phase_renderer import PhaseRenderer, ToolExecutionCard

# Catppuccin Mocha background — matches TUI background
_BG_COLOR = "#1e1e2e"


class _CatppuccinCodeBlock(TextElement):
    """Code block that forces background_color to match the TUI theme."""

    style_name = "markdown.code_block"

    @classmethod
    def create(cls, markdown: "Markdown", token: Token) -> "_CatppuccinCodeBlock":
        node_info = token.info or ""
        lexer_name = node_info.partition(" ")[0]
        return cls(lexer_name or "text", markdown.code_theme)

    def __init__(self, lexer_name: str, theme: str) -> None:
        self.lexer_name = lexer_name
        self.theme = theme

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        code = str(self.text).rstrip()
        syntax = Syntax(
            code,
            self.lexer_name,
            theme=self.theme,
            word_wrap=True,
            padding=1,
            background_color=_BG_COLOR,
        )
        yield syntax


class PihuMarkdown(Markdown):
    """Markdown subclass that uses Catppuccin-themed code blocks with matching bg."""

    elements = {**Markdown.elements, "code_block": _CatppuccinCodeBlock}


class StatusContext:
    """Context manager for live console.status() inside Textual TUI."""

    def __init__(self, adapter: TextualConsoleAdapter, message: str, spinner: str = "dots"):
        self.adapter = adapter
        self.message = message
        self.spinner = spinner

    def __enter__(self):
        try:
            log_widget = getattr(self.adapter, "log", None)
            if log_widget and hasattr(log_widget, "app") and log_widget.app:
                log_widget.app.set_activity_status(self.message)
        except Exception:
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            log_widget = getattr(self.adapter, "log", None)
            if log_widget and hasattr(log_widget, "app") and log_widget.app:
                log_widget.app.clear_activity_status()
        except Exception:
            pass


def _get_catppuccin_code_theme() -> str:
    try:
        import pygments.styles
        if "catppuccin-mocha" in pygments.styles.STYLE_MAP:
            return "catppuccin-mocha"
        if "catppuccin-macchiato" in pygments.styles.STYLE_MAP:
            return "catppuccin-macchiato"
    except Exception:
        pass
    return "dracula"


class TextualConsoleAdapter:
    """
    Adapter bridging PihuAgent's Rich Console output to Textual's RichLog widget.
    Ensures Markdown responses get rendered with dark Catppuccin IDE code themes.
    """

    def __init__(self, rich_log: RichLog):
        self.log = rich_log

    def write(self, renderable: Any) -> None:
        """Write any Rich renderable or Markdown object into RichLog."""
        try:
            self.log.write(renderable)
        except Exception:
            pass

    def print(self, *args, **kwargs) -> None:
        """Emulate Console.print() by sending formatted Rich objects to RichLog."""
        if not args:
            return

        for arg in args:
            if isinstance(arg, (Markdown, Panel, Table, Syntax, Text)):
                self.write(arg)
            elif isinstance(arg, str):
                if (arg.startswith("[dim]") or arg.startswith("Pihu ›") or arg.startswith("  [")) and "\n" not in arg:
                    txt = Text.from_markup(arg) if "[" in arg and "]" in arg else Text(arg)
                    self.write(txt)
                else:
                    md = PihuMarkdown(arg, code_theme=_get_catppuccin_code_theme())
                    self.write(md)
            else:
                self.write(Text(str(arg)))

    def status(self, message: str, spinner: str = "dots") -> StatusContext:
        """Return context manager emulating console.status()."""
        return StatusContext(self, message, spinner)

    def render_tool_group(self, tool_cards: List[ToolExecutionCard]) -> None:
        """Render a list of executed tools in a grouped box matching reference UI."""
        if not tool_cards:
            return
        panel = PhaseRenderer.render_grouped_tools(tool_cards)
        self.write(panel)

    def render_phase(self, title: str, body: str, icon: str = "✦", color: str = "#89b4fa") -> None:
        """Render a step phase (e.g. Understanding, Planning)."""
        panel = PhaseRenderer.render_phase(title, body, icon, color)
        self.write(panel)

    def input(self, prompt: str = "") -> str:
        """Fallback input handler."""
        return ""
