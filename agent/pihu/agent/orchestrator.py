import uuid
import time
import json
from typing import Optional, List, Dict, Any
from pihu.agent.pipeline import ExecutionState, TaskContext
from pihu.events.bus import bus
from pihu.events.types import AgentEvent, EventType
from pihu.llm.router import ModelRouter
from pihu.llm.base import Message, ToolCall
from pihu.mcp.manager import MCPManager
from pihu.security.permissions import SecurityManager
from pihu.context.engine import ContextEngine
from pihu.intent.engine import IntentResolver, IntentPath
from pihu.mcp.retriever import ToolRetriever
from pihu.memory.db import db_engine
from pihu.formatter import format_human_response

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

        # Initialize database schema
        await db_engine.initialize()

        await self.transition(context, ExecutionState.RECEIVED, f"Task received: '{prompt}'")
        await self.transition(context, ExecutionState.UNDERSTANDING, "Analyzing task intent and requirements...")

        # Fast Path check via IntentResolver
        path, fast_tool, fast_args = IntentResolver.classify(prompt)
        if path == IntentPath.FAST_PATH and fast_tool:
            if fast_tool == "greeting":
                ans = fast_args.get("text", "Hello!")
                await self.transition(context, ExecutionState.COMPLETED, "Fast path greeting completed")
                return ans

            # Try running the fast tool directly if available
            discovered_tools = await self.mcp_manager.load_and_initialize()
            if fast_tool in self.mcp_manager.tool_map:
                await self.transition(context, ExecutionState.EXECUTING, f"Fast Path executing: {fast_tool}")
                try:
                    tool_output = await self.mcp_manager.execute_tool(fast_tool, fast_args or {})
                    await db_engine.record_activity("FAST_TOOL_EXECUTED", fast_tool, fast_args)
                    formatted_ans = format_human_response(fast_tool, tool_output, fast_args)
                    await self.transition(context, ExecutionState.COMPLETED, "Fast path execution completed")
                    return formatted_ans
                except Exception as err:
                    pass  # Fall through to full agent pipeline on error

        await self.transition(context, ExecutionState.CONTEXT_LOADING, "Gathering system and environment context...")
        system_context_str = self.context_engine.render_system_context_prompt()

        # Initialize MCP Manager tools
        discovered_tools = await self.mcp_manager.load_and_initialize()

        # Filter relevant tools using ToolRetriever
        relevant_tools = ToolRetriever.retrieve_relevant_tools(
            query=prompt,
            all_tools=discovered_tools,
            tool_map=self.mcp_manager.tool_map,
            top_k=8
        )

        await self.transition(
            context,
            ExecutionState.TOOL_SELECTION,
            f"Available MCP tools: {len(discovered_tools)} (filtered to top {len(relevant_tools)})",
            details={"tools": [t.name for t in relevant_tools]}
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
        seen_tool_signatures = []

        while turns < max_turns:
            turns += 1

            await self.transition(context, ExecutionState.MODEL_SELECTION, f"Turn {turns}: Routing prompt to optimal LLM provider")
            response = await self.router.generate(
                task_prompt=prompt,
                messages=messages,
                tools=relevant_tools if relevant_tools else None,
                preferred_provider=preferred_provider,
                preferred_model=preferred_model
            )

            if response.content:
                final_answer = response.content
                messages.append(Message(role="assistant", content=response.content, raw_parts=response.raw_parts))

            if response.tool_calls:
                await self.transition(context, ExecutionState.EXECUTING, f"Model requested {len(response.tool_calls)} tool call(s)")

                for tc in response.tool_calls:
                    sig = (tc.name, json.dumps(tc.arguments, sort_keys=True))
                    if seen_tool_signatures.count(sig) >= 2:
                        await self.transition(context, ExecutionState.OBSERVING, f"Breaking repeated tool loop for {tc.name}")
                        break
                    seen_tool_signatures.append(sig)

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
                        await db_engine.record_activity("TOOL_EXECUTED", tc.name, tc.arguments)
                    except Exception as err:
                        tool_output = f"Error executing tool {tc.name}: {str(err)}"

                    await self.transition(context, ExecutionState.OBSERVING, f"Observed output from {tc.name}")
                    messages.append(Message(role="assistant", content=response.content, tool_calls=[tc], raw_parts=response.raw_parts))
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
        target_server: Optional[str] = None,
    ) -> str:
        """Run a task with live Rich console output showing each step."""
        from rich.panel import Panel
        from rich.text import Text
        from rich import box

        task_id = f"task_{uuid.uuid4().hex[:8]}"
        started = time.perf_counter()

        await db_engine.initialize()
        system_context_str = self.context_engine.render_system_context_prompt()

        # Initialize MCP tools if not already done
        if not self.mcp_manager.tools:
            discovered_tools = await self.mcp_manager.load_and_initialize()
        else:
            discovered_tools = self.mcp_manager.tools

        # Fast Path check via IntentResolver inside run_task_interactive
        path, fast_tool, fast_args = IntentResolver.classify(prompt)
        if path == IntentPath.FAST_PATH and fast_tool and not target_server:
            if fast_tool == "greeting":
                reply = fast_args.get("text", "Hello!")
                console.print()
                console.print(Text.assemble(("Pihu", "bold bright_green"), (" › ", "dim")), end="")
                console.print(reply)
                console.print()
                return reply

            if fast_tool in self.mcp_manager.tool_map:
                fast_started = time.perf_counter()
                with console.status(f"[bold yellow]◌ Running {fast_tool}...[/bold yellow]", spinner="dots"):
                    try:
                        tool_output = await self.mcp_manager.execute_tool(fast_tool, fast_args or {})
                        await db_engine.record_activity("FAST_TOOL_EXECUTED", fast_tool, fast_args)
                        fast_elapsed = time.perf_counter() - fast_started
                        reply = format_human_response(fast_tool, tool_output, fast_args)

                        console.print()
                        console.print(Text.assemble(("Pihu", "bold bright_green"), (" › ", "dim")), end="")
                        console.print(reply)
                        console.print(f"[dim]fast MCP • {fast_elapsed:.3f}s[/dim]\n")
                        return reply
                    except Exception as err:
                        console.print(f"  [dim red]Fast path error ({err}), falling back to agent...[/dim red]")

        # Retrieve relevant tools using ToolRetriever or filter by target_server
        if target_server:
            relevant_tools = [
                t for t in discovered_tools
                if self.mcp_manager.tool_map.get(t.name, (None, None))[0] == target_server
            ]
            if not relevant_tools:
                relevant_tools = discovered_tools
        else:
            relevant_tools = ToolRetriever.retrieve_relevant_tools(
                query=prompt,
                all_tools=discovered_tools,
                tool_map=self.mcp_manager.tool_map,
                top_k=8
            )

        target_instr = f"\nTARGET MCP SERVER: Focus on tools from the '{target_server}' server." if target_server else ""

        # Setup messages with conversation history
        sys_msg = Message(
            role="system",
            content=(
                "You are PIHU (Personalized Intelligent Human Utility), an expert AI agent.\n"
                "Help the user complete their task directly and clearly.\n"
                "Use available MCP tools when necessary to query information or perform actions.\n"
                "Primary tools for files are from pihu-file-mcp (e.g. list_directory, stat_file, read_file, write_file).\n"
                "Primary tools for system are from pihu-system-mcp (e.g. get_system_info, get_system_status).\n"
                "Keep your answers concise and natural." + target_instr + "\n\n"
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
        seen_tool_signatures = []

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
                    tools=relevant_tools if relevant_tools else None,
                    preferred_provider=preferred_provider,
                    preferred_model=preferred_model,
                )

            provider_name = response.provider
            model_name = response.model

            if response.content:
                final_answer = response.content

            if response.tool_calls:
                should_break_loop = False
                tool_cards = []

                for tc in response.tool_calls:
                    sig = (tc.name, json.dumps(tc.arguments, sort_keys=True))
                    if seen_tool_signatures.count(sig) >= 2:
                        console.print(f"  [yellow]⚠ Repeated tool call detected for '{tc.name}'. Finalizing response.[/yellow]")
                        should_break_loop = True
                        break
                    seen_tool_signatures.append(sig)

                    server = "mcp"
                    if tc.name in self.mcp_manager.tool_map:
                        server = self.mcp_manager.tool_map[tc.name][0]

                    perm_check = await self.security.check_permission(tc.name, tc.arguments)
                    if perm_check.requires_user_approval:
                        console.print(f"  [yellow]⚠ {tc.name} requires approval (auto-approved)[/yellow]")

                    tool_started = time.perf_counter()
                    with console.status(
                        f"[bold #a6e3a1]⠋ Running {tc.name}...[/bold #a6e3a1]",
                        spinner="dots",
                    ):
                        try:
                            tool_output = await self.mcp_manager.execute_tool(tc.name, tc.arguments)
                            await db_engine.record_activity("TOOL_EXECUTED", tc.name, tc.arguments)
                            is_success = not tool_output.startswith("Error")
                        except Exception as err:
                            tool_output = f"Error: {str(err)}"
                            is_success = False

                    tool_elapsed = time.perf_counter() - tool_started

                    from pihu.ui.phase_renderer import ToolExecutionCard, format_tool_summary
                    summary = format_tool_summary(tc.name, tool_output)

                    card = ToolExecutionCard(
                        server=server,
                        tool_name=tc.name,
                        elapsed_sec=tool_elapsed,
                        output_summary=summary,
                        success=is_success,
                    )
                    tool_cards.append(card)

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

                # Render grouped tools step box if adapter supports it
                if hasattr(console, "render_tool_group") and tool_cards:
                    console.render_tool_group(tool_cards)

                if should_break_loop:
                    break
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
        "pihu-file-mcp": ("◫", "cyan"),
        "pihu-system-mcp": ("⚙", "green"),
        "filesystem": ("◫", "cyan"),
        "memory": ("◆", "magenta"),
        "fetch": ("↗", "blue"),
        "time": ("◷", "yellow"),
        "system": ("⚙", "green"),
    }
    return meta.get(server, ("●", "bright_white"))
