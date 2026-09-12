"""
PIHU Interactive REPL — Rich-based terminal interface.

Supports slash commands: /tools, /mcp, /model, /provider, /help, /clear, /exit
"""

import asyncio
from contextlib import suppress
from datetime import datetime
from typing import List

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from pihu.agent.orchestrator import PihuAgent
from pihu.mcp.manager import MCPManager
from pihu.config.settings import settings
from pihu.llm.base import Message
from pihu.intent.engine import IntentResolver, IntentPath
from pihu.memory.db import db_engine

try:
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice
    HAS_INQUIRER = True
except ImportError:
    HAS_INQUIRER = False

console = Console(highlight=False)


# ============================================================
# FAST PATH — bypass LLM for trivial queries
# ============================================================

def local_response(text: str):
    """Instant responses for greetings and thanks."""
    t = text.lower().strip()
    greetings = {"hi", "hello", "hey", "hii", "hiii", "yo", "sup"}
    if t in greetings:
        return "Hey! 👋 What can I help you with?"
    if t in {"thanks", "thank you", "thx", "ty"}:
        return "You're welcome! 😊"
    if t in {"bye", "goodbye"}:
        return "Goodbye! 👋"
    return None


def local_timezone_name():
    """Best-effort IANA timezone for fast time queries."""
    try:
        tz = datetime.now().astimezone().tzinfo
        key = getattr(tz, "key", None)
        if key:
            return key
    except Exception:
        pass
    return "UTC"


def fast_call_for(text: str, tool_names: list):
    """Check if this query can be fast-pathed to a known MCP tool."""
    t = text.lower().strip()
    time_phrases = (
        "what time is it", "current time", "time right now",
        "what's the time", "whats the time", "time now",
    )
    if "get_current_time" in tool_names and any(p in t for p in time_phrases):
        return "get_current_time", {"timezone": local_timezone_name()}
    return None


# ============================================================
# DISPLAY HELPERS
# ============================================================

def show_startup_banner(provider: str, model: str, server_count: int, tool_count: int):
    grid = Table.grid(padding=(0, 2))
    grid.add_row(
        Text("✦ Pihu", style="bold bright_white"),
        Text("Personalized Intelligent Human Utility", style="dim"),
    )
    grid.add_row(
        Text("Provider", style="cyan"),
        Text(f"{provider} • {model}", style="white"),
    )
    grid.add_row(
        Text("MCP", style="green"),
        Text(f"{server_count} servers • {tool_count} tools", style="white"),
    )

    console.print(Panel(
        grid,
        border_style="bright_cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    ))


async def show_tools(mcp_manager: MCPManager):
    """Display all MCP tools in a Rich table, with interactive InquirerPy fuzzy search if available."""
    if HAS_INQUIRER and mcp_manager.tools:
        choices = []
        for tool in sorted(mcp_manager.tools, key=lambda t: t.name):
            server = mcp_manager.tool_map.get(tool.name, ("unknown", ""))[0]
            choices.append(Choice(value=tool, name=f"[{server:<14}] {tool.name:<25} • {tool.description[:60]}"))

        try:
            selected_tool = await inquirer.fuzzy(
                message="Search & Inspect MCP Tool Catalog:",
                choices=choices,
                match_exact=False,
            ).execute_async()
            if selected_tool:
                console.print(Panel(
                    f"[bold white]Tool:[/bold white] {selected_tool.name}\n"
                    f"[bold white]Description:[/bold white] {selected_tool.description}\n"
                    f"[bold white]Parameters:[/bold white] {json.dumps(selected_tool.parameters, indent=2)}",
                    title=f"[cyan]MCP Tool Info: {selected_tool.name}[/cyan]",
                    border_style="cyan",
                    box=box.ROUNDED,
                ))
                console.print()
                return
        except Exception:
            pass

    table = Table(
        title="MCP Tool Catalog",
        box=box.ROUNDED,
        border_style="bright_cyan",
        header_style="bold cyan",
    )
    table.add_column("Server", style="cyan", no_wrap=True)
    table.add_column("Tool", style="white")
    table.add_column("Description", style="dim", max_width=60)

    for tool in sorted(mcp_manager.tools, key=lambda t: t.name):
        server = "unknown"
        if tool.name in mcp_manager.tool_map:
            server = mcp_manager.tool_map[tool.name][0]
        table.add_row(server, tool.name, tool.description[:80])

    console.print(table)
    console.print()


def show_mcp_servers(mcp_manager: MCPManager):
    """Display connected MCP servers with tool counts."""
    counts = {}
    for tool in mcp_manager.tools:
        if tool.name in mcp_manager.tool_map:
            server = mcp_manager.tool_map[tool.name][0]
            counts[server] = counts.get(server, 0) + 1

    table = Table(
        title="Connected MCP Servers",
        box=box.ROUNDED,
        border_style="green",
        header_style="bold green",
    )
    table.add_column("Server", style="bold white")
    table.add_column("Tools", justify="right", style="cyan")
    table.add_column("Status", style="bold green")

    for server_name in sorted(mcp_manager.sessions.keys()):
        session = mcp_manager.sessions[server_name]
        count = counts.get(server_name, 0)
        status = "● connected" if session.session else "○ disconnected"
        status_style = "bold green" if session.session else "bold red"
        table.add_row(server_name, str(count), Text(status, style=status_style))

    console.print(table)
    console.print()


async def show_model_selector(agent: PihuAgent, current_provider: str, current_model: str):
    """Interactive model selector using InquirerPy with fuzzy search."""
    with console.status("[bold cyan]◌ Discovering available models...[/bold cyan]", spinner="dots"):
        available = await agent.router.discover_models()

    all_options = []

    # Ollama (local) models
    if "ollama" in available and available["ollama"]:
        for m in available["ollama"]:
            name = m["name"]
            size = f"{m.get('size_gb', '?')}GB"
            all_options.append(("ollama", name, f"ollama:{name} ({size}) [local]"))

    # Gemini (cloud) models
    if "gemini" in available and available["gemini"]:
        for m in available["gemini"]:
            name = m["name"]
            desc = m.get("description", "")
            all_options.append(("gemini", name, f"gemini:{name} ({desc}) [cloud]"))

    if HAS_INQUIRER and all_options:
        choices = [
            Choice(value=(prov, mod), name=label)
            for prov, mod, label in all_options
        ]
        try:
            default_val = (current_provider, current_model) if any((prov == current_provider and mod == current_model) for prov, mod, _ in all_options) else choices[0].value
            selected = await inquirer.select(
                message="Select PIHU Model:",
                choices=choices,
                default=default_val,
                cycle=True,
            ).execute_async()
            if selected:
                new_prov, new_mod = selected
                console.print(f"  [bold green]✓[/bold green] Switched to {new_prov}:{new_mod}\n")
                return new_prov, new_mod
        except Exception:
            pass

    # Fallback to Rich terminal list if InquirerPy unavailable or interrupted
    index = 1
    fallback_options = []
    if "ollama" in available and available["ollama"]:
        console.print(Text("\n  Local Models (Ollama)", style="bold cyan"))
        for m in available["ollama"]:
            name = m["name"]
            size = f"{m.get('size_gb', '?')}GB"
            param = m.get("parameter_size", "")
            marker = " ◀ active" if name == current_model and current_provider == "ollama" else ""
            console.print(f"    {index:2d}) {name:<35} [dim]{param} • {size}[/dim]{marker}")
            fallback_options.append(("ollama", name))
            index += 1

    if "gemini" in available and available["gemini"]:
        console.print(Text("\n  Cloud Models (Gemini)", style="bold magenta"))
        for m in available["gemini"]:
            name = m["name"]
            desc = m.get("description", "")
            marker = " ◀ active" if name == current_model and current_provider == "gemini" else ""
            console.print(f"    {index:2d}) {name:<35} [dim]{desc}[/dim]{marker}")
            fallback_options.append(("gemini", name))
            index += 1

    console.print()
    choice = console.input("[bold cyan]Select model (number or name): [/bold cyan]").strip()

    if not choice:
        return current_provider, current_model

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(fallback_options):
            new_provider, new_model = fallback_options[idx]
            console.print(f"  [bold green]✓[/bold green] Switched to {new_provider}:{new_model}\n")
            return new_provider, new_model
    except ValueError:
        pass

    if choice.startswith("gemini"):
        console.print(f"  [bold green]✓[/bold green] Switched to gemini:{choice}\n")
        return "gemini", choice
    else:
        console.print(f"  [bold green]✓[/bold green] Switched to ollama:{choice}\n")
        return "ollama", choice


def show_help():
    table = Table(
        title="PIHU Commands",
        box=box.ROUNDED,
        border_style="bright_cyan",
        header_style="bold cyan",
    )
    table.add_column("Command", style="bold white", no_wrap=True)
    table.add_column("Description", style="dim")

    commands = [
        ("/tools", "List all available MCP tools"),
        ("/mcp", "Show connected MCP servers and status"),
        ("/model", "Interactive model selector (local + cloud)"),
        ("/model <name>", "Quick switch to a specific model"),
        ("/provider", "Toggle between ollama and gemini"),
        ("/clear", "Clear conversation context and terminal"),
        ("/help", "Show this help message"),
        ("/exit", "Exit PIHU"),
    ]
    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)
    console.print()


def print_pihu(text: str):
    console.print(
        Text.assemble(
            ("Pihu", "bold bright_green"),
            (": ", "bright_green"),
            (text, "white"),
        )
    )
    console.print()


# ============================================================
# MAIN REPL
# ============================================================

async def run_repl(
    initial_provider: str = "",
    initial_model: str = "",
):
    """Main PIHU interactive REPL — launches Textual IDE TUI."""
    from pihu.ui.app import run_tui_async
    await run_tui_async(initial_provider, initial_model)


async def run_single_task(
    prompt: str,
    provider: str = "",
    model: str = "",
):
    """Run a single task with Rich output (non-REPL mode)."""
    current_provider = provider or settings.default_provider
    current_model = model or (
        settings.gemini_model if current_provider == "gemini" else settings.ollama_model
    )

    mcp_manager = MCPManager()
    agent = PihuAgent(mcp_manager=mcp_manager)

    try:
        await agent.run_task_interactive(
            prompt=prompt,
            console=console,
            preferred_provider=current_provider,
            preferred_model=current_model,
        )
    except Exception as e:
        console.print(Panel(str(e), title="[red]Error[/red]", border_style="red"))
    finally:
        with suppress(Exception):
            await mcp_manager.close_all()
