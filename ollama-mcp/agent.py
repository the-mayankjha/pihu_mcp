import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from google import genai
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# =========================================================
# CONFIG
# =========================================================

MODEL = "gemini-3.8-flash"
THINKING_LEVEL = "low"

BASE_DIR = Path(__file__).resolve().parent

SERVER_PATHS = [
    BASE_DIR / "servers" / "system.py",
    BASE_DIR / "server.py",
]

SYSTEM_PROMPT = """
You are Pihu, a fast, helpful local computer assistant.

You have access to tools running locally through MCP.

Rules:
- Use local MCP tools when they are needed for the user's computer.
- OS, CPU, RAM, disk, and Python information -> get_system_info.
- Battery -> get_battery.
- Date/time -> get_current_time.
- Local environment -> get_environment.
- Never invent local computer information.
- Do not expose raw function-call JSON.
- Keep ordinary answers concise and natural.
- Never claim a local action succeeded unless the tool returned success.
"""


# =========================================================
# TERMINAL UI
# =========================================================

console = Console(highlight=False)


TOOL_UI = {
    "get_current_time": {
        "icon": "◷",
        "color": "cyan",
        "label": "Time & Date",
        "fast": True,
    },

    "get_system_info": {
        "icon": "◈",
        "color": "blue",
        "label": "System Info",
        "fast": True,
    },

    "get_battery": {
        "icon": "⚡",
        "color": "yellow",
        "label": "Battery",
        "fast": True,
    },

    "get_environment": {
        "icon": "⌂",
        "color": "magenta",
        "label": "Environment",
        "fast": True,
    },

    "add": {
        "icon": "＋",
        "color": "green",
        "label": "Calculator",
        "fast": False,
    },

    "greet": {
        "icon": "✦",
        "color": "green",
        "label": "Greeting",
        "fast": False,
    },
}


def tool_meta(name):
    return TOOL_UI.get(
        name,
        {
            "icon": "◆",
            "color": "bright_cyan",
            "label": name.replace("_", " ").title(),
            "fast": False,
        },
    )


def startup_panel():
    table = Table.grid(padding=(0, 2))

    table.add_row(
        Text("Pihu AI", style="bold white"),
        Text("local agent", style="dim"),
    )

    table.add_row(
        Text("Gemini 3.8 Flash", style="cyan"),
        Text(
            f"thinking: {THINKING_LEVEL}",
            style="magenta",
        ),
    )

    table.add_row(
        Text("MCP", style="green"),
        Text("online", style="green"),
    )

    return Panel(
        table,
        border_style="bright_cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    )


def status_spinner(text, color="cyan"):
    return console.status(
        f"[bold {color}]{text}[/bold {color}]",
        spinner="dots",
    )


def print_pihu(text):
    console.print(
        Text.assemble(
            ("Pihu", "bold bright_green"),
            (": ", "bright_green"),
            (text, "white"),
        )
    )


def print_user_prompt():
    return console.input(
        "[bold bright_cyan]You[/bold bright_cyan]"
        "[dim]:[/dim] "
    ).strip()


def tool_panel(
    name,
    arguments=None,
    running=False,
):
    meta = tool_meta(name)

    body = Text()

    status = (
        "RUNNING"
        if running
        else "READY"
    )

    status_style = (
        "yellow"
        if running
        else "green"
    )

    body.append(
        f"{meta['icon']}  ",
        style=f"bold {meta['color']}",
    )

    body.append(
        meta["label"],
        style="bold white",
    )

    body.append(
        f"  {status}",
        style=f"bold {status_style}",
    )

    if arguments:

        try:
            args_text = json.dumps(
                arguments,
                ensure_ascii=False,
                separators=(", ", ": "),
            )

        except Exception:
            args_text = str(arguments)

        body.append("\n")
        body.append(
            "args  ",
            style="dim",
        )
        body.append(
            args_text,
            style="dim",
        )

    return Panel(
        body,
        title=(
            f"[{meta['color']}]"
            f"MCP • {name}"
            f"[/]"
        ),
        border_style=meta["color"],
        box=box.ROUNDED,
        padding=(0, 1),
    )


# =========================================================
# GEMINI
# =========================================================

api_key = os.environ.get(
    "GEMINI_API_KEY"
)

if not api_key:

    console.print(
        Panel(
            "GEMINI_API_KEY is not set.\n\n"
            "Run:\n"
            "[bold]export GEMINI_API_KEY='YOUR_KEY'[/bold]",
            title="[red]Configuration Error[/red]",
            border_style="red",
        )
    )

    raise SystemExit(1)


client = genai.Client(
    api_key=api_key
)


# =========================================================
# MCP
# =========================================================

def make_gemini_tool(mcp_tool):

    schema = (
        mcp_tool.input_schema
        or {
            "type": "object",
            "properties": {},
        }
    )

    return {
        "type": "function",
        "name": mcp_tool.name,
        "description": (
            mcp_tool.description
            or mcp_tool.name
        ),
        "parameters": schema,
    }


def format_mcp_result(result):

    structured = getattr(
        result,
        "structured_content",
        None,
    )

    if structured is not None:

        if isinstance(
            structured,
            dict,
        ):
            return structured

        if isinstance(
            structured,
            str,
        ):

            try:
                return json.loads(
                    structured
                )

            except json.JSONDecodeError:
                return structured

        return structured

    output = []

    for block in getattr(
        result,
        "content",
        [],
    ):

        text = getattr(
            block,
            "text",
            None,
        )

        if text:
            output.append(text)

    text = "\n".join(
        output
    ).strip()

    if not text:
        return {}

    try:
        return json.loads(text)

    except json.JSONDecodeError:
        return text


async def connect_mcp_servers():

    clients = []
    tools = []
    tool_map = {}

    with status_spinner(
        "Connecting to local MCP servers",
        "cyan",
    ):

        for server_path in SERVER_PATHS:

            params = StdioServerParameters(
                command=sys.executable,
                args=[
                    str(server_path)
                ],
            )

            mcp_client = Client(
                params
            )

            await mcp_client.__aenter__()

            clients.append(
                mcp_client
            )

            result = await (
                mcp_client.list_tools()
            )

            for tool in result.tools:

                if tool.name in tool_map:

                    raise RuntimeError(
                        f"Duplicate MCP tool: "
                        f"{tool.name}"
                    )

                tool_map[
                    tool.name
                ] = mcp_client

                tools.append(
                    make_gemini_tool(
                        tool
                    )
                )

    return (
        clients,
        tools,
        tool_map,
    )


# =========================================================
# LOCAL FAST ROUTER
# =========================================================

def local_response(text):

    t = text.lower().strip()

    if t in {
        "hi",
        "hello",
        "hey",
        "hii",
        "hiii",
        "yo",
        "sup",
    }:

        return (
            "Hey! 👋 "
            "What can I help you with?"
        )

    if t in {
        "thanks",
        "thank you",
        "thx",
        "ty",
    }:

        return "You're welcome! 😎"

    if t in {
        "bye",
        "goodbye",
        "see you",
        "cya",
    }:

        return "See you! 👋"

    return None


def detect_fast_tool(text):

    t = text.lower().strip()

    # -----------------------------------------------------
    # Battery
    # -----------------------------------------------------

    if any(
        word in t
        for word in (
            "battery",
            "charge",
            "charging",
        )
    ):

        return "get_battery"

    # -----------------------------------------------------
    # Time / date
    # -----------------------------------------------------

    time_words = (
        "what time",
        "current time",
        "time right now",
        "time now",
        "what's the time",
        "whats the time",
    )

    date_words = (
        "what date",
        "today's date",
        "todays date",
        "current date",
        "date today",
    )

    if any(
        word in t
        for word in (
            *time_words,
            *date_words,
        )
    ):

        return "get_current_time"

    # -----------------------------------------------------
    # System information
    # -----------------------------------------------------

    system_patterns = (
        "what operating system",
        "which operating system",
        "what os",
        "which os",
        "what cpu",
        "which cpu",
        "how much ram",
        "how much memory",
        "memory usage",
        "ram usage",
        "disk space",
        "disk usage",
        "python version",
        "what version of python",
        "computer specs",
        "system information",
    )

    if any(
        pattern in t
        for pattern in system_patterns
    ):

        return "get_system_info"

    # -----------------------------------------------------
    # Environment
    # -----------------------------------------------------

    environment_patterns = (
        "current directory",
        "current folder",
        "working directory",
        "what shell",
        "which shell",
        "home directory",
    )

    if any(
        pattern in t
        for pattern in environment_patterns
    ):

        return "get_environment"

    return None


async def run_fast_tool(
    tool_name,
    tool_map,
):

    mcp_client = tool_map.get(
        tool_name
    )

    if mcp_client is None:

        return {
            "error":
            f"Tool not found: {tool_name}"
        }

    result = await (
        mcp_client.call_tool(
            tool_name,
            {},
        )
    )

    return format_mcp_result(
        result
    )


def friendly_fast_result(
    tool_name,
    result,
):

    if not isinstance(
        result,
        dict,
    ):

        return str(result)

    # -----------------------------------------------------
    # Battery
    # -----------------------------------------------------

    if tool_name == "get_battery":

        if not result.get(
            "available",
            False,
        ):

            return (
                "I can't access the "
                "battery information right now."
            )

        percentage = result.get(
            "percentage",
            "unknown",
        )

        charging = result.get(
            "charging",
            False,
        )

        status = (
            "charging"
            if charging
            else "not charging"
        )

        answer = (
            f"Your battery is at "
            f"**{percentage}%** and is "
            f"**{status}**."
        )

        time_left = result.get(
            "time_left_minutes"
        )

        if time_left:

            hours, minutes = divmod(
                time_left,
                60,
            )

            if hours:

                remaining = (
                    f"{hours}h"
                )

                if minutes:
                    remaining += (
                        f" {minutes}m"
                    )

            else:

                remaining = (
                    f"{minutes}m"
                )

            answer += (
                f" Estimated battery time "
                f"remaining: **{remaining}**."
            )

        return answer

    # -----------------------------------------------------
    # Time
    # -----------------------------------------------------

    if tool_name == "get_current_time":

        day = result.get(
            "day",
            "",
        )

        date = result.get(
            "date",
            "",
        )

        current_time = result.get(
            "time",
            "",
        )

        try:

            parsed = datetime.strptime(
                current_time,
                "%H:%M:%S",
            )

            friendly_time = (
                parsed.strftime(
                    "%-I:%M %p"
                )
            )

        except Exception:

            friendly_time = current_time

        return (
            f"It's **{day}, {date}**, "
            f"and the current time is "
            f"**{friendly_time}**."
        )

    # -----------------------------------------------------
    # System
    # -----------------------------------------------------

    if tool_name == "get_system_info":

        return (
            f"You're running "
            f"**{result.get('os', 'unknown')}** "
            f"on **{result.get('architecture', 'unknown')}** "
            f"with **{result.get('cpu_count', '?')} CPU cores**. "
            f"RAM usage is **"
            f"{result.get('memory_used_gb', '?')} / "
            f"{result.get('memory_total_gb', '?')} GB**, "
            f"with **{result.get('disk_free_gb', '?')} GB** "
            f"of disk space free. "
            f"Python: **{result.get('python', '?')}**."
        )

    # -----------------------------------------------------
    # Environment
    # -----------------------------------------------------

    if tool_name == "get_environment":

        return (
            f"Your current directory is "
            f"**{result.get('current_directory', 'unknown')}**, "
            f"your shell is "
            f"**{result.get('shell', 'unknown')}**, "
            f"and your home directory is "
            f"**{result.get('home', 'unknown')}**."
        )

    return json.dumps(
        result,
        ensure_ascii=False,
        default=str,
    )


async def handle_fast_path(
    tool_name,
    tool_map,
):

    started = time.perf_counter()

    meta = tool_meta(
        tool_name
    )

    with status_spinner(
        f"{meta['icon']}  Reading local system",
        meta["color"],
    ):

        result = await run_fast_tool(
            tool_name,
            tool_map,
        )

    elapsed = (
        time.perf_counter()
        - started
    )

    console.print(
        tool_panel(
            tool_name,
            running=False,
        )
    )

    answer = friendly_fast_result(
        tool_name,
        result,
    )

    # Remove markdown markers because
    # we're using Text output here.
    answer = answer.replace(
        "**",
        "",
    )

    print_pihu(
        answer
    )

    console.print(
        f"[dim]local tool • "
        f"{elapsed:.3f}s[/dim]\n"
    )


# =========================================================
# GEMINI STREAMING
# =========================================================

def start_gemini_stream(
    user_input,
    gemini_tools,
    previous_interaction_id=None,
):

    kwargs = {
        "model": MODEL,

        "input": (
            SYSTEM_PROMPT
            + "\n\nUser:\n"
            + user_input
        ),

        "tools": gemini_tools,

        "stream": True,

        "generation_config": {
            "thinking_level":
                THINKING_LEVEL,

            # We show a safe visual
            # "Thinking..." state instead
            # of exposing internal reasoning.
            "thinking_summaries":
                "none",
        },
    }

    if previous_interaction_id:

        kwargs[
            "previous_interaction_id"
        ] = previous_interaction_id

    return client.interactions.create(
        **kwargs
    )


def collect_stream(stream):

    interaction_id = None

    tool_calls = {}

    answer_started = False

    status = status_spinner(
        "Thinking",
        "magenta",
    )

    status.start()

    try:

        for event in stream:

            event_type = getattr(
                event,
                "event_type",
                None,
            )

            # -------------------------------------------------
            # Interaction created
            # -------------------------------------------------

            if (
                event_type
                == "interaction.created"
            ):

                interaction = getattr(
                    event,
                    "interaction",
                    None,
                )

                if interaction:

                    interaction_id = (
                        interaction.id
                    )

            # -------------------------------------------------
            # Step started
            # -------------------------------------------------

            elif (
                event_type
                == "step.start"
            ):

                step = getattr(
                    event,
                    "step",
                    None,
                )

                if not step:
                    continue

                step_type = getattr(
                    step,
                    "type",
                    None,
                )

                # Do NOT expose thought content.
                if step_type == "thought":

                    status.update(
                        "[bold magenta]"
                        "Thinking"
                        "[/bold magenta]"
                    )

                elif (
                    step_type
                    == "function_call"
                ):

                    status.update(
                        "[bold yellow]"
                        "Preparing tool call"
                        "[/bold yellow]"
                    )

                    tool_calls[
                        event.index
                    ] = {
                        "id": step.id,
                        "name": step.name,
                        "arguments": "",
                    }

            # -------------------------------------------------
            # Stream delta
            # -------------------------------------------------

            elif (
                event_type
                == "step.delta"
            ):

                delta = getattr(
                    event,
                    "delta",
                    None,
                )

                if not delta:
                    continue

                delta_type = getattr(
                    delta,
                    "type",
                    None,
                )

                # Safe thought status.
                if (
                    delta_type
                    == "thought_summary"
                ):

                    status.update(
                        "[bold magenta]"
                        "Thinking"
                        "[/bold magenta]"
                    )

                # Model text.
                elif (
                    delta_type
                    == "text"
                ):

                    text = getattr(
                        delta,
                        "text",
                        None,
                    )

                    if text:

                        if not answer_started:

                            status.stop()

                            console.print(
                                "\n"
                                "[bold bright_green]"
                                "Pihu"
                                "[/bold bright_green]"
                                "[dim]:[/dim] ",
                                end="",
                            )

                            answer_started = True

                        console.print(
                            text,
                            end="",
                            soft_wrap=True,
                        )

                # Function-call arguments.
                elif delta_type in {
                    "arguments",
                    "arguments_delta",
                }:

                    arguments = getattr(
                        delta,
                        "arguments",
                        None,
                    )

                    if (
                        arguments
                        and event.index
                        in tool_calls
                    ):

                        tool_calls[
                            event.index
                        ]["arguments"] += (
                            arguments
                        )

            # -------------------------------------------------
            # Interaction completed
            # -------------------------------------------------

            elif (
                event_type
                == "interaction.completed"
            ):

                interaction = getattr(
                    event,
                    "interaction",
                    None,
                )

                if interaction:

                    interaction_id = (
                        interaction.id
                    )

        if answer_started:
            console.print()

    finally:

        status.stop()

    return (
        interaction_id,
        list(
            tool_calls.values()
        ),
    )


# =========================================================
# TOOL EXECUTION
# =========================================================

async def execute_tool_calls(
    tool_calls,
    tool_map,
):

    results = []

    for call in tool_calls:

        tool_name = call[
            "name"
        ]

        raw_arguments = call.get(
            "arguments",
            "",
        )

        try:

            arguments = json.loads(
                raw_arguments or "{}"
            )

        except json.JSONDecodeError:

            arguments = {}

        meta = tool_meta(
            tool_name
        )

        console.print(
            tool_panel(
                tool_name,
                arguments,
                running=True,
            )
        )

        started = time.perf_counter()

        with status_spinner(
            f"{meta['icon']}  Running "
            f"{tool_name}",
            meta["color"],
        ):

            mcp_client = tool_map.get(
                tool_name
            )

            if mcp_client is None:

                result = {
                    "error":
                    f"Unknown MCP tool: "
                    f"{tool_name}"
                }

            else:

                try:

                    mcp_result = (
                        await mcp_client.call_tool(
                            tool_name,
                            arguments,
                        )
                    )

                    result = (
                        format_mcp_result(
                            mcp_result
                        )
                    )

                except Exception as exc:

                    result = {
                        "error":
                        str(exc)
                    }

        elapsed = (
            time.perf_counter()
            - started
        )

        console.print(
            f"[bold green]✓[/bold green] "
            f"[{meta['color']}]"
            f"{tool_name}[/] "
            f"[dim]completed in "
            f"{elapsed:.3f}s[/dim]"
        )

        results.append(
            {
                "type":
                    "function_result",

                "name":
                    tool_name,

                "call_id":
                    call["id"],

                "result":
                    [
                        {
                            "type":
                                "text",

                            "text":
                                json.dumps(
                                    result,
                                    ensure_ascii=False,
                                    default=str,
                                ),
                        }
                    ],
            }
        )

    console.print()

    return results


# =========================================================
# GEMINI RESULT STREAM
# =========================================================

def start_result_stream(
    interaction_id,
    results,
    gemini_tools,
):

    return client.interactions.create(
        model=MODEL,

        previous_interaction_id=(
            interaction_id
        ),

        input=results,

        tools=gemini_tools,

        stream=True,

        generation_config={
            "thinking_level":
                THINKING_LEVEL,

            "thinking_summaries":
                "none",
        },
    )


async def run_gemini_turn(
    user_input,
    gemini_tools,
    tool_map,
    previous_interaction_id=None,
):

    started = time.perf_counter()

    try:

        stream = start_gemini_stream(
            user_input,
            gemini_tools,
            previous_interaction_id,
        )

        (
            interaction_id,
            tool_calls,
        ) = collect_stream(
            stream
        )

    except Exception as exc:

        error_text = str(exc)

        # Recover from expired/invalid
        # server-side conversation state.
        if (
            "404" in error_text
            or
            "Requested entity was not found"
            in error_text
        ):

            console.print(
                "[yellow]↻ Gemini conversation "
                "state expired — starting "
                "a fresh turn.[/yellow]"
            )

            try:

                stream = start_gemini_stream(
                    user_input,
                    gemini_tools,
                    None,
                )

                (
                    interaction_id,
                    tool_calls,
                ) = collect_stream(
                    stream
                )

            except Exception as retry_exc:

                console.print(
                    Panel(
                        str(retry_exc),
                        title=(
                            "[red]"
                            "Gemini Error"
                            "[/red]"
                        ),
                        border_style="red",
                    )
                )

                return None

        else:

            console.print(
                Panel(
                    error_text,
                    title=(
                        "[red]"
                        "Gemini Error"
                        "[/red]"
                    ),
                    border_style="red",
                )
            )

            return None

    # -----------------------------------------------------
    # No tool
    # -----------------------------------------------------

    if not tool_calls:

        elapsed = (
            time.perf_counter()
            - started
        )

        console.print(
            f"[dim]Gemini • "
            f"{elapsed:.2f}s[/dim]\n"
        )

        return interaction_id

    # -----------------------------------------------------
    # Execute tools
    # -----------------------------------------------------

    results = (
        await execute_tool_calls(
            tool_calls,
            tool_map,
        )
    )

    # -----------------------------------------------------
    # Continue after tools
    # -----------------------------------------------------

    while True:

        try:

            stream = start_result_stream(
                interaction_id,
                results,
                gemini_tools,
            )

            (
                next_interaction_id,
                more_tool_calls,
            ) = collect_stream(
                stream
            )

            interaction_id = (
                next_interaction_id
                or interaction_id
            )

        except Exception as exc:

            console.print(
                Panel(
                    str(exc),
                    title=(
                        "[red]"
                        "Tool Continuation Error"
                        "[/red]"
                    ),
                    border_style="red",
                )
            )

            return interaction_id

        if not more_tool_calls:
            break

        results = (
            await execute_tool_calls(
                more_tool_calls,
                tool_map,
            )
        )

    elapsed = (
        time.perf_counter()
        - started
    )

    console.print(
        f"[dim]Gemini + tools • "
        f"{elapsed:.2f}s[/dim]\n"
    )

    return interaction_id


# =========================================================
# COMMANDS
# =========================================================

def show_tools(gemini_tools):

    table = Table(
        title="Available MCP Tools",
        box=box.ROUNDED,
        border_style="bright_cyan",
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column(
        "Tool",
        style="white",
    )

    table.add_column(
        "Purpose",
        style="dim",
    )

    table.add_column(
        "Mode",
        justify="center",
    )

    for tool in gemini_tools:

        name = tool["name"]

        meta = tool_meta(
            name
        )

        mode = (
            "[green]FAST[/green]"
            if meta["fast"]
            else "[magenta]AI[/magenta]"
        )

        table.add_row(
            f"{meta['icon']} {name}",
            meta["label"],
            mode,
        )

    console.print(
        table
    )

    console.print()


# =========================================================
# MAIN
# =========================================================

async def main():

    console.print(
        startup_panel()
    )

    clients = []

    previous_interaction_id = None

    try:

        (
            clients,
            gemini_tools,
            tool_map,
        ) = await connect_mcp_servers()

        console.print(
            f"[bold green]✓[/bold green] "
            f"Connected • "
            f"[cyan]"
            f"{len(gemini_tools)} MCP tools"
            f"[/cyan]"
        )

        console.print()

        show_tools(
            gemini_tools
        )

        console.print(
            "[dim]"
            "Commands: /tools  /clear  /exit"
            "[/dim]\n"
        )

        while True:

            user_input = (
                print_user_prompt()
            )

            if not user_input:
                continue

            command = (
                user_input.lower()
            )

            # -------------------------------------------------
            # Exit
            # -------------------------------------------------

            if command in {
                "/exit",
                "/quit",
                "exit",
                "quit",
            }:

                break

            # -------------------------------------------------
            # Tools
            # -------------------------------------------------

            if command == "/tools":

                show_tools(
                    gemini_tools
                )

                continue

            # -------------------------------------------------
            # Clear conversation
            # -------------------------------------------------

            if command == "/clear":

                previous_interaction_id = (
                    None
                )

                console.print(
                    "[green]✓ AI conversation "
                    "context cleared.[/green]\n"
                )

                continue

            # -------------------------------------------------
            # Instant local responses
            # -------------------------------------------------

            local = local_response(
                user_input
            )

            if local:

                print_pihu(
                    local
                )

                console.print()

                continue

            # -------------------------------------------------
            # Fast MCP path
            # -------------------------------------------------

            fast_tool = (
                detect_fast_tool(
                    user_input
                )
            )

            if fast_tool:

                await handle_fast_path(
                    fast_tool,
                    tool_map,
                )

                continue

            # -------------------------------------------------
            # Gemini
            # -------------------------------------------------

            previous_interaction_id = (
                await run_gemini_turn(
                    user_input,
                    gemini_tools,
                    tool_map,
                    previous_interaction_id,
                )
            )

    finally:

        for mcp_client in clients:

            try:

                await mcp_client.__aexit__(
                    None,
                    None,
                    None,
                )

            except Exception:
                pass

        console.print(
            "\n[dim]"
            "Pihu offline. Goodbye 👋"
            "[/dim]"
        )


if __name__ == "__main__":
    asyncio.run(main())
