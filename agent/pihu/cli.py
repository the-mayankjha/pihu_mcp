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


def show_tools(mcp_manager: MCPManager):
    """Display all MCP tools in a Rich table."""
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
    """Interactive model selector showing available local + cloud models."""
    with console.status("[bold cyan]◌ Discovering available models...[/bold cyan]", spinner="dots"):
        available = await agent.router.discover_models()

    all_options = []
    index = 1

    # Ollama (local) models
    if "ollama" in available and available["ollama"]:
        console.print(Text("\n  Local Models (Ollama)", style="bold cyan"))
        for m in available["ollama"]:
            name = m["name"]
            size = f"{m.get('size_gb', '?')}GB"
            param = m.get("parameter_size", "")
            marker = " ◀ active" if name == current_model and current_provider == "ollama" else ""
            console.print(f"    {index:2d}) {name:<35} [dim]{param} • {size}[/dim]{marker}")
            all_options.append(("ollama", name))
            index += 1
    else:
        console.print(Text("\n  Local Models (Ollama)", style="bold cyan"))
        console.print("    [dim]Ollama not running or no models installed[/dim]")

    # Gemini (cloud) models
    if "gemini" in available and available["gemini"]:
        console.print(Text("\n  Cloud Models (Gemini)", style="bold magenta"))
        for m in available["gemini"]:
            name = m["name"]
            desc = m.get("description", "")
            marker = " ◀ active" if name == current_model and current_provider == "gemini" else ""
            console.print(f"    {index:2d}) {name:<35} [dim]{desc}[/dim]{marker}")
            all_options.append(("gemini", name))
            index += 1

    console.print()
    choice = console.input("[bold cyan]Select model (number or name): [/bold cyan]").strip()

    if not choice:
        return current_provider, current_model

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(all_options):
            new_provider, new_model = all_options[idx]
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
    """Main PIHU interactive REPL loop with context retention."""
    current_provider = initial_provider or settings.default_provider
    current_model = initial_model or (
        settings.gemini_model if current_provider == "gemini" else settings.ollama_model
    )

    mcp_manager = MCPManager()
    agent = PihuAgent(mcp_manager=mcp_manager)

    # Initialize MCP servers
    console.print(
        Panel(
            "[bold cyan]Discovering MCP servers and tools…[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    try:
        discovered_tools = await mcp_manager.load_and_initialize()
    except Exception as e:
        console.print(f"[bold red]✗ MCP initialization failed: {e}[/bold red]")
        discovered_tools = []

    for server_name in sorted(mcp_manager.sessions.keys()):
        tool_count = sum(
            1 for name, (srv, _) in mcp_manager.tool_map.items()
            if srv == server_name and "__" not in name
        )
        console.print(
            f"  [bold green]✓[/bold green] {server_name:<14} "
            f"[dim]{tool_count} tools[/dim]"
        )
    console.print()

    # Startup banner
    show_startup_banner(
        provider=current_provider,
        model=current_model,
        server_count=len(mcp_manager.sessions),
        tool_count=len(discovered_tools),
    )

    console.print("[dim]/tools  /mcp  /model  /help  /exit[/dim]\n")

    # Session conversation memory across REPL prompts
    session_history: List[Message] = []

    try:
        while True:
            try:
                user_input = console.input(
                    f"[bold bright_cyan]pihu[/bold bright_cyan]"
                    f"[dim]({current_provider}:{current_model})[/dim]"
                    f"[bold bright_cyan] › [/bold bright_cyan]"
                ).strip()
            except EOFError:
                break
            except KeyboardInterrupt:
                console.print()
                continue

            if not user_input:
                continue

            command = user_input.lower()

            if command in {"/exit", "/quit", "exit", "quit"}:
                break

            if command == "/tools":
                show_tools(mcp_manager)
                continue

            if command in {"/mcp", "/servers"}:
                show_mcp_servers(mcp_manager)
                continue

            if command == "/model" or command.startswith("/model "):
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    new_model = parts[1].strip()
                    if new_model.startswith("gemini"):
                        current_provider = "gemini"
                    else:
                        current_provider = "ollama"
                    current_model = new_model
                    console.print(f"  [bold green]✓[/bold green] Switched to {current_provider}:{current_model}\n")
                else:
                    current_provider, current_model = await show_model_selector(
                        agent, current_provider, current_model
                    )
                continue

            if command == "/provider":
                if current_provider == "ollama":
                    current_provider = "gemini"
                    current_model = settings.gemini_model
                else:
                    current_provider = "ollama"
                    current_model = settings.ollama_model
                console.print(f"  [bold green]✓[/bold green] Switched to {current_provider}:{current_model}\n")
                continue

            if command == "/help":
                show_help()
                continue

            if command == "/clear":
                session_history.clear()
                console.print("\033[H\033[2J", end="")
                console.print("[green]✓ Cleared conversation context and screen.[/green]\n")
                continue

            local = local_response(user_input)
            if local:
                session_history.append(Message(role="user", content=user_input))
                session_history.append(Message(role="assistant", content=local))
                print_pihu(local)
                continue

            tool_names = [t.name for t in discovered_tools]
            fast = fast_call_for(user_input, tool_names)
            if fast:
                import time as _time
                tool_name, arguments = fast
                fast_started = _time.perf_counter()

                with console.status(
                    "[bold yellow]◌ Running MCP tool...[/bold yellow]",
                    spinner="dots",
                ):
                    try:
                        result = await mcp_manager.execute_tool(tool_name, arguments)
                    except Exception as e:
                        result = f"Error: {e}"

                fast_elapsed = _time.perf_counter() - fast_started

                import json
                try:
                    data = json.loads(result)
                    dt_str = data.get("datetime", result)
                    tz = data.get("timezone", "")
                    day = data.get("day_of_week", "")
                    reply = f"It's {dt_str} ({day}) in {tz}"
                except (json.JSONDecodeError, TypeError):
                    reply = str(result)

                session_history.append(Message(role="user", content=user_input))
                session_history.append(Message(role="assistant", content=reply))

                print_pihu(reply)
                console.print(f"[dim]fast MCP • {fast_elapsed:.3f}s[/dim]\n")
                continue

            # Append current user prompt to session history
            session_history.append(Message(role="user", content=user_input))

            try:
                await agent.run_task_interactive(
                    prompt=user_input,
                    console=console,
                    history=session_history,
                    preferred_provider=current_provider,
                    preferred_model=current_model,
                )
            except Exception as e:
                console.print(
                    Panel(
                        str(e),
                        title="[red]Error[/red]",
                        border_style="red",
                    )
                )
                console.print()

    finally:
        with suppress(Exception):
            await mcp_manager.close_all()
        console.print("\n[dim]Pihu offline. Goodbye 👋[/dim]")


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
