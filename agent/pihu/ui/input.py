from __future__ import annotations

from typing import List, Optional, Set
from textual.suggester import Suggester

BASE_COMMANDS: List[str] = [
    "/help",
    "/tools",
    "/mcp",
    "/servers",
    "/model",
    "/model gemini-3.6-flash",
    "/model gemini-1.5-flash",
    "/model gemini-1.5-pro",
    "/model qwen3:4b",
    "/model gemma3:4b",
    "/model llama3:8b",
    "/provider",
    "/provider key",
    "/key",
    "/key GEMINI_API_KEY",
    "/key PIHU_WEB_SEARCH_API_KEY",
    "/key OPENAI_API_KEY",
    "/key ANTHROPIC_API_KEY",
    "/config",
    "/config pihu_web_search",
    "/cd",
    "/cd ~",
    "/search",
    "/explore",
    "/memory",
    "/project",
    "/context",
    "/offline",
    "/clear",
    "/exit",
]


class PihuCommandSuggester(Suggester):
    """Context-aware dynamic command suggester for PIHU TUI Input."""

    def __init__(self, commands: Optional[List[str]] = None, case_sensitive: bool = False):
        super().__init__(case_sensitive=case_sensitive)
        self._commands_set: Set[str] = set(commands or BASE_COMMANDS)
        self.commands: List[str] = sorted(self._commands_set)

    def add_commands(self, new_cmds: List[str]) -> None:
        """Dynamically add new model names, tool names, or server names to autosuggestions."""
        for cmd in new_cmds:
            if cmd:
                self._commands_set.add(cmd.strip())
        self.commands = sorted(self._commands_set)

    async def get_suggestion(self, value: str) -> str | None:
        if not value or not value.startswith("/"):
            return None

        val_lower = value.lower() if not self.case_sensitive else value
        for cmd in self.commands:
            cmd_cmp = cmd.lower() if not self.case_sensitive else cmd
            if cmd_cmp.startswith(val_lower) and cmd_cmp != val_lower:
                return cmd

        return None
