from __future__ import annotations

import asyncio
from typing import List, Tuple, Optional
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, OptionList
from textual.widgets.option_list import Option

from pihu.llm.ollama import OllamaProvider
from pihu.llm.gemini import GeminiProvider
from pihu.config.settings import settings


class CommandPaletteModal(ModalScreen[str]):
    """Command Palette modal popup positioned right above the input bar."""

    DEFAULT_CSS = """
    CommandPaletteModal {
        align: center bottom;
        padding-bottom: 4;
        background: rgba(0, 0, 0, 0.4);
    }

    #palette-container {
        width: 66;
        height: auto;
        max-height: 18;
        background: #1e1e2e;
        border: round #cba6f7;
        padding: 1 2;
    }

    #palette-title {
        text-style: bold;
        color: #cba6f7;
        margin-bottom: 1;
    }

    #palette-search {
        margin-bottom: 1;
        border: round #45475a;
        background: #313244;
    }

    OptionList {
        background: transparent;
        border: none;
        max-height: 10;
    }
    """

    COMMANDS = [
        ("/model", "Switch LLM model (interactive selector)"),
        ("/mcp", "View connected MCP servers & tools"),
        ("/tools", "Open searchable MCP Tool Catalog"),
        ("/provider", "Toggle between Ollama and Gemini"),
        ("/offline", "Toggle offline mode (Ollama local only)"),
        ("/clear", "Clear conversation screen"),
        ("/help", "Show command reference guide"),
        ("/exit", "Quit PIHU terminal application"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="palette-container"):
            yield Label("✦ Command Palette", id="palette-title")
            yield Input(placeholder="Type command or search...", id="palette-search")
            yield OptionList(*self._build_options(""), id="palette-options")

    def _build_options(self, query: str) -> List[Option]:
        options = []
        q = query.lower()
        for cmd, desc in self.COMMANDS:
            if q and q not in cmd and q not in desc.lower():
                continue
            options.append(Option(f"{cmd:<14} › {desc}", id=cmd))
        return options

    def on_input_changed(self, event: Input.Changed) -> None:
        opt_list = self.query_one("#palette-options", OptionList)
        opt_list.clear_options()
        for opt in self._build_options(event.value):
            opt_list.add_option(opt)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        cmd_id = str(event.option.id)
        self.dismiss(cmd_id)

    def on_key(self, event) -> None:
        if event.key in ("escape", "ctrl+c"):
            self.dismiss("")


class ModelSelectModal(ModalScreen[Tuple[str, str]]):
    """Modal screen for interactive model selection with dynamic discovery."""

    DEFAULT_CSS = """
    ModelSelectModal {
        align: center bottom;
        padding-bottom: 4;
        background: rgba(0, 0, 0, 0.4);
    }

    #modal-container {
        width: 66;
        height: auto;
        max-height: 18;
        background: #1e1e2e;
        border: round #cba6f7;
        padding: 1 2;
    }

    #modal-title {
        text-style: bold;
        color: #cba6f7;
        margin-bottom: 1;
    }

    OptionList {
        background: transparent;
        border: none;
        max-height: 12;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-container"):
            yield Label("✦ Select LLM Model (Loading...)", id="modal-title")
            yield OptionList(Option("Discovering available models...", id="loading"), id="model-options")

    async def on_mount(self) -> None:
        self.load_dynamic_models()

    @work(exclusive=True, group="load-models")
    async def load_dynamic_models(self) -> None:
        title = self.query_one("#modal-title", Label)
        opt_list = self.query_one("#model-options", OptionList)

        default_gemini = [
            ("gemini", settings.gemini_model, f"{settings.gemini_model} (Cloud Default)"),
            ("gemini", "gemini-1.5-flash", "gemini-1.5-flash (Gemini Cloud)"),
            ("gemini", "gemini-1.5-pro", "gemini-1.5-pro (Gemini Cloud)"),
        ]
        default_ollama = [
            ("ollama", settings.ollama_model, f"{settings.ollama_model} (Ollama Local Default)"),
            ("ollama", "gemma3:4b", "gemma3:4b (Ollama Local)"),
            ("ollama", "llama3:8b", "llama3:8b (Ollama Local)"),
        ]

        discovered_options: List[Tuple[str, str, str]] = []

        try:
            g_prov = GeminiProvider()
            g_models = await g_prov.list_models()
            if g_models:
                for m in g_models:
                    m_name = m.get("name", "")
                    desc = m.get("description", m_name)
                    discovered_options.append(("gemini", m_name, f"{m_name} ({desc})"))
            else:
                discovered_options.extend(default_gemini)

            o_prov = OllamaProvider()
            o_models = await o_prov.list_models()
            if o_models:
                for m in o_models:
                    m_name = m.get("name", "")
                    sz = m.get("size_gb", 0)
                    sz_str = f" • {sz}GB" if sz else ""
                    discovered_options.append(("ollama", m_name, f"{m_name}{sz_str} (Ollama Local)"))
            else:
                discovered_options.extend(default_ollama)

        except Exception:
            discovered_options = default_gemini + default_ollama

        seen = set()
        final_options = []
        for prov, mod, label in discovered_options:
            key = f"{prov}:{mod}"
            if key not in seen:
                seen.add(key)
                final_options.append((prov, mod, label))

        opt_list.clear_options()
        for prov, mod, label in final_options:
            opt_list.add_option(Option(f"[{prov}] {label}", id=f"{prov}:{mod}"))

        title.update("✦ Select LLM Model")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        option_id = str(event.option.id)
        if option_id == "loading":
            return
        if ":" in option_id:
            provider, model = option_id.split(":", 1)
            self.dismiss((provider, model))

    def on_key(self, event) -> None:
        if event.key in ("escape", "ctrl+c"):
            self.dismiss(("", ""))


class MCPListModal(ModalScreen[None]):
    """Modal screen displaying connected MCP servers."""

    DEFAULT_CSS = """
    MCPListModal {
        align: center bottom;
        padding-bottom: 4;
        background: rgba(0, 0, 0, 0.4);
    }

    #mcp-modal-container {
        width: 66;
        height: auto;
        max-height: 18;
        background: #1e1e2e;
        border: round #94e2d5;
        padding: 1 2;
    }

    #mcp-modal-title {
        text-style: bold;
        color: #94e2d5;
        margin-bottom: 1;
    }
    """

    def __init__(self, mcp_manager):
        super().__init__()
        self.mcp_manager = mcp_manager

    def compose(self) -> ComposeResult:
        with Vertical(id="mcp-modal-container"):
            yield Label("✦ Connected MCP Servers", id="mcp-modal-title")
            options = []
            counts = {}
            for tool in self.mcp_manager.tools:
                if tool.name in self.mcp_manager.tool_map:
                    srv = self.mcp_manager.tool_map[tool.name][0]
                    counts[srv] = counts.get(srv, 0) + 1

            for server in sorted(self.mcp_manager.sessions.keys()):
                session = self.mcp_manager.sessions[server]
                st = "ONLINE" if session.session else "OFFLINE"
                tc = counts.get(server, 0)
                options.append(Option(f"● {server:<18} [{st}]  • {tc} tools", id=server))

            yield OptionList(*options, id="mcp-options")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key in ("escape", "ctrl+c", "enter"):
            self.dismiss(None)


class ToolListModal(ModalScreen[None]):
    """Modal screen with searchable tool catalog."""

    DEFAULT_CSS = """
    ToolListModal {
        align: center bottom;
        padding-bottom: 4;
        background: rgba(0, 0, 0, 0.4);
    }

    #tool-modal-container {
        width: 76;
        height: 20;
        background: #1e1e2e;
        border: round #89b4fa;
        padding: 1 2;
    }

    #tool-modal-title {
        text-style: bold;
        color: #89b4fa;
        margin-bottom: 1;
    }

    #tool-search {
        margin-bottom: 1;
        border: round #45475a;
        background: #313244;
    }

    OptionList {
        background: transparent;
        height: 1fr;
    }
    """

    def __init__(self, mcp_manager):
        super().__init__()
        self.mcp_manager = mcp_manager
        self.all_tools = sorted(mcp_manager.tools, key=lambda x: x.name)

    def compose(self) -> ComposeResult:
        with Vertical(id="tool-modal-container"):
            yield Label("✦ MCP Tool Catalog", id="tool-modal-title")
            yield Input(placeholder="Search tools...", id="tool-search")
            yield OptionList(*self._build_options(""), id="tool-options")

    def _build_options(self, query: str) -> List[Option]:
        options = []
        q = query.lower()
        for tool in self.all_tools:
            server = self.mcp_manager.tool_map.get(tool.name, ("unknown", None))[0]
            if q and q not in tool.name.lower() and q not in (tool.description or "").lower() and q not in server.lower():
                continue
            desc = (tool.description or "")[:40]
            text = f"{server:<16} › {tool.name:<22} ({desc})"
            options.append(Option(text, id=tool.name))
        return options

    def on_input_changed(self, event: Input.Changed) -> None:
        opt_list = self.query_one("#tool-options", OptionList)
        opt_list.clear_options()
        for opt in self._build_options(event.value):
            opt_list.add_option(opt)

    def on_key(self, event) -> None:
        if event.key in ("escape", "ctrl+c"):
            self.dismiss(None)
