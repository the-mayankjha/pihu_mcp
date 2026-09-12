import sys
import asyncio
import argparse
from pihu.events.bus import bus


async def async_main(args):
    if args.json:
        # JSON IPC mode for Go CLI
        bus.emit_to_stdout = True

        if not args.prompt:
            print('{"type":"ERROR","message":"No prompt provided"}')
            sys.exit(1)

        from pihu.agent.orchestrator import PihuAgent
        agent = PihuAgent()
        try:
            await agent.run_task(
                prompt=args.prompt,
                preferred_provider=args.provider,
                preferred_model=args.model,
            )
        finally:
            await agent.mcp_manager.close_all()

    elif args.prompt:
        # Single task with Rich output
        from pihu.cli import run_single_task
        await run_single_task(
            prompt=args.prompt,
            provider=args.provider or "",
            model=args.model or "",
        )


def main():
    parser = argparse.ArgumentParser(description="PIHU - Personalized Intelligent Human Utility")
    parser.add_argument("prompt", type=str, nargs="?", help="Task prompt for PIHU to execute")
    parser.add_argument("--json", action="store_true", help="Emit events as JSON-Lines only (for Go CLI IPC)")
    parser.add_argument("--provider", type=str, choices=["ollama", "gemini"], help="Preferred LLM provider")
    parser.add_argument("--model", type=str, help="Preferred model name (e.g. qwen3:4b, gemini-2.0-flash)")
    args = parser.parse_args()

    try:
        if args.json or args.prompt:
            asyncio.run(async_main(args))
        else:
            # Interactive REPL mode: Run Textual TUI directly on main thread
            from pihu.ui.app import run_tui
            run_tui(provider=args.provider or "", model=args.model or "")
    except KeyboardInterrupt:
        print("\n[PIHU] Goodbye!")


if __name__ == "__main__":
    main()
