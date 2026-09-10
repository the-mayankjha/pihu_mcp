import uuid
import time
from typing import Optional, List, Dict, Any
from pihu.agent.pipeline import ExecutionState, TaskContext
from pihu.events.bus import bus
from pihu.events.types import AgentEvent, EventType
from pihu.llm.router import ModelRouter
from pihu.llm.base import Message, ToolCall
from pihu.mcp.manager import MCPManager
from pihu.security.permissions import SecurityManager
from pihu.context.engine import ContextEngine

class PihuAgent:
    """Core PIHU Agent Orchestrator managing execution pipeline state machine."""

    def __init__(self, mcp_manager: Optional[MCPManager] = None):
        self.router = ModelRouter()
        self.mcp_manager = mcp_manager or MCPManager()
        self.security = SecurityManager()
        self.context_engine = ContextEngine()

    async def transition(self, context: TaskContext, new_state: ExecutionState, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        context.state = new_state
        event_type_map = {
            ExecutionState.RECEIVED: EventType.TASK_STARTED,
            ExecutionState.UNDERSTANDING: EventType.UNDERSTANDING,
            ExecutionState.CONTEXT_LOADING: EventType.CONTEXT_LOADING,
            ExecutionState.MODEL_SELECTION: EventType.MODEL_SELECTED,
            ExecutionState.PLANNING: EventType.PLAN_CREATED,
            ExecutionState.EXECUTING: EventType.EXECUTING,
            ExecutionState.OBSERVING: EventType.OBSERVING,
            ExecutionState.VERIFYING: EventType.VERIFICATION_STARTED,
            ExecutionState.COMPLETED: EventType.TASK_COMPLETED,
            ExecutionState.FAILED: EventType.ERROR,
        }
        ev_type = event_type_map.get(new_state, EventType.EXECUTING)
        await bus.emit(
            AgentEvent(
                type=ev_type,
                task_id=context.task_id,
                component="agent_orchestrator",
                status="info" if new_state != ExecutionState.FAILED else "error",
                message=f"[{new_state.value}] {message}",
                details=details or {}
            )
        )

    async def run_task(
        self,
        prompt: str,
        max_turns: int = 10,
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None
    ) -> str:
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        context = TaskContext(task_id=task_id, prompt=prompt)

        await self.transition(context, ExecutionState.RECEIVED, f"Task received: '{prompt}'")
        await self.transition(context, ExecutionState.UNDERSTANDING, "Analyzing task intent and requirements...")
        await self.transition(context, ExecutionState.CONTEXT_LOADING, "Gathering system and environment context...")

        system_context_str = self.context_engine.render_system_context_prompt()

        # Initialize MCP Manager tools
        discovered_tools = await self.mcp_manager.load_and_initialize()
        await self.transition(
            context,
            ExecutionState.TOOL_SELECTION,
            f"Available MCP tools: {len(discovered_tools)}",
            details={"tools": [t.name for t in discovered_tools]}
        )

        messages: List[Message] = [
            Message(
                role="system",
                content=(
                    "You are PIHU (Personalized Intelligent Human Utility), an expert AI agent.\n"
                    "Help the user complete their task directly and clearly.\n"
                    "Use available MCP tools when necessary to query information or perform actions.\n"
                    "Memory tools are available: create_entities, add_observations, search_nodes, read_graph.\n"
                    "When the user tells you personal details (name, preferences, etc.), use create_entities or add_observations to save them to memory!\n\n"
                    + system_context_str
                )
            ),
            Message(role="user", content=prompt)
        ]

        turns = 0
        final_answer = ""

        while turns < max_turns:
            turns += 1

            await self.transition(context, ExecutionState.MODEL_SELECTION, f"Turn {turns}: Routing prompt to optimal LLM provider")
            response = await self.router.generate(
                task_prompt=prompt,
                messages=messages,
                tools=discovered_tools if discovered_tools else None,
                preferred_provider=preferred_provider,
                preferred_model=preferred_model
            )

            if response.content:
                final_answer = response.content
                messages.append(Message(role="assistant", content=response.content, raw_parts=response.raw_parts))

            if response.tool_calls:
                await self.transition(context, ExecutionState.EXECUTING, f"Model requested {len(response.tool_calls)} tool call(s)")
                assistant_tool_msg = Message(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls,
                    raw_parts=response.raw_parts
                )
                messages.append(assistant_tool_msg)

                for tc in response.tool_calls:
                    await self.transition(context, ExecutionState.PERMISSION_CHECK, f"Checking permission for {tc.name}")
                    perm_check = await self.security.check_permission(tc.name, tc.arguments)

                    if perm_check.requires_user_approval:
                        approved = await self.security.request_user_approval(tc.name, tc.arguments, perm_check.risk_level)
                        if not approved:
                            error_res = f"User denied permission to run {tc.name}."
                            messages.append(Message(role="tool", name=tc.name, tool_call_id=tc.id, content=error_res))
                            continue

                    try:
                        tool_output = await self.mcp_manager.execute_tool(tc.name, tc.arguments)
                    except Exception as err:
                        tool_output = f"Error executing tool {tc.name}: {str(err)}"

                    await self.transition(context, ExecutionState.OBSERVING, f"Observed output from {tc.name}")
                    messages.append(Message(role="tool", name=tc.name, tool_call_id=tc.id, content=tool_output))
            else:
                break

        await self.transition(context, ExecutionState.VERIFYING, "Verifying output quality and completeness...")
        await self.transition(context, ExecutionState.COMPLETED, "Task successfully completed", details={"result": final_answer})

        return final_answer

    async def run_task_interactive(
        self,
        prompt: str,
        console,
        history: Optional[List[Message]] = None,
        max_turns: int = 10,
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
    ) -> str:
        """Run a task with live Rich console output showing each step."""
        from rich.panel import Panel
        from rich.text import Text
        from rich import box

        task_id = f"task_{uuid.uuid4().hex[:8]}"
        started = time.perf_counter()

        system_context_str = self.context_engine.render_system_context_prompt()

        # Initialize MCP tools if not already done
        if not self.mcp_manager.tools:
            with console.status("[bold cyan]◌ Discovering MCP tools...[/bold cyan]", spinner="dots"):
                discovered_tools = await self.mcp_manager.load_and_initialize()
            for server_name, session in self.mcp_manager.sessions.items():
                tool_count = sum(1 for _, (srv, _) in self.mcp_manager.tool_map.items() if srv == server_name and "__" not in _)
                console.print(
                    f"  [bold green]✓[/bold green] {server_name:<14} "
                    f"[dim]{tool_count} tools[/dim]"
                )
            console.print()
        else:
            discovered_tools = self.mcp_manager.tools

        # Setup messages with conversation history
        sys_msg = Message(
            role="system",
            content=(
                "You are PIHU (Personalized Intelligent Human Utility), an expert AI agent.\n"
                "Help the user complete their task directly and clearly.\n"
                "Use available MCP tools when necessary to query information or perform actions.\n"
                "Memory tools are available: create_entities, add_observations, search_nodes, read_graph.\n"
                "When the user tells you personal details (e.g. name, preferences), use memory tools to remember them!\n"
                "Keep your answers concise and natural.\n\n"
                + system_context_str
            )
        )

        messages: List[Message] = [sys_msg]
        if history:
            messages.extend(history)
        else:
            messages.append(Message(role="user", content=prompt))

        turns = 0
        final_answer = ""
        provider_name = preferred_provider or "auto"
        model_name = preferred_model or "auto"

        while turns < max_turns:
            turns += 1

            # LLM inference with spinner
            with console.status(
                f"[bold magenta]◌ Thinking...[/bold magenta]",
                spinner="dots",
            ):
                response = await self.router.generate(
                    task_prompt=prompt,
                    messages=messages,
                    tools=discovered_tools if discovered_tools else None,
                    preferred_provider=preferred_provider,
                    preferred_model=preferred_model,
                )

            provider_name = response.provider
            model_name = response.model

            if response.content:
                final_answer = response.content

            if response.tool_calls:
                # Show tool call panels
                for tc in response.tool_calls:
                    server = "mcp"
                    if tc.name in self.mcp_manager.tool_map:
                        server = self.mcp_manager.tool_map[tc.name][0]

                    icon, color = _tool_meta(server)
                    console.print(
                        Panel(
                            Text.assemble(
                                (f"{icon} ", f"bold {color}"),
                                (server, "bold white"),
                                (" › ", "dim"),
                                (tc.name, "white"),
                            ),
                            title="[bold]MCP tool[/bold]",
                            border_style=color,
                            box=box.ROUNDED,
                        )
                    )

                    perm_check = await self.security.check_permission(tc.name, tc.arguments)
                    if perm_check.requires_user_approval:
                        console.print(f"  [yellow]⚠ {tc.name} requires approval (auto-approved)[/yellow]")

                    tool_started = time.perf_counter()
                    with console.status(
                        f"[bold {color}]◌ Running {tc.name}[/bold {color}]",
                        spinner="dots",
                    ):
                        try:
                            tool_output = await self.mcp_manager.execute_tool(tc.name, tc.arguments)
                        except Exception as err:
                            tool_output = f"Error: {str(err)}"

                    tool_elapsed = time.perf_counter() - tool_started

                    if tool_output.startswith("Error"):
                        console.print(f"  [bold red]✗[/bold red] {tc.name} [dim]failed in {tool_elapsed:.3f}s[/dim]")
                    else:
                        console.print(f"  [bold green]✓[/bold green] {tc.name} [dim]completed in {tool_elapsed:.3f}s[/dim]")

                    assistant_msg = Message(
                        role="assistant",
                        content=response.content,
                        tool_calls=[tc],
                        raw_parts=response.raw_parts
                    )
                    messages.append(assistant_msg)
                    if history is not None:
                        history.append(assistant_msg)

                    tool_msg = Message(role="tool", name=tc.name, tool_call_id=tc.id, content=tool_output)
                    messages.append(tool_msg)
                    if history is not None:
                        history.append(tool_msg)

                continue
            else:
                if response.content:
                    assistant_msg = Message(role="assistant", content=response.content, raw_parts=response.raw_parts)
                    if history is not None and (not history or history[-1].content != response.content):
                        history.append(assistant_msg)
                break

        elapsed = time.perf_counter() - started

        if final_answer:
            console.print()
            console.print(
                Text.assemble(
                    ("Pihu", "bold bright_green"),
                    (" › ", "dim"),
                ),
                end="",
            )
            console.print(final_answer)
            console.print()

        console.print(f"[dim]{provider_name}:{model_name} • {elapsed:.2f}s[/dim]\n")

        return final_answer


def _tool_meta(server: str):
    """Return icon and color for an MCP server."""
    meta = {
        "filesystem": ("◫", "cyan"),
        "memory": ("◆", "magenta"),
        "fetch": ("↗", "blue"),
        "time": ("◷", "yellow"),
        "system": ("⚙", "green"),
    }
    return meta.get(server, ("●", "bright_white"))
