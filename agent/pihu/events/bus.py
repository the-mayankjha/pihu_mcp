import asyncio
import sys
import json
from typing import Callable, List, Awaitable
from pihu.events.types import AgentEvent

EventListener = Callable[[AgentEvent], Awaitable[None]]

class EventBus:
    """Central event bus for publishing and subscribing to AgentEvents."""

    def __init__(self, emit_to_stdout: bool = False):
        self.listeners: List[EventListener] = []
        self.emit_to_stdout = emit_to_stdout

    def subscribe(self, listener: EventListener) -> None:
        if listener not in self.listeners:
            self.listeners.append(listener)

    def unsubscribe(self, listener: EventListener) -> None:
        if listener in self.listeners:
            self.listeners.remove(listener)

    async def emit(self, event: AgentEvent) -> None:
        if self.emit_to_stdout:
            sys.stdout.write(event.model_dump_json() + "\n")
            sys.stdout.flush()

        tasks = [listener(event) for listener in self.listeners]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

# Global default event bus
bus = EventBus(emit_to_stdout=False)
