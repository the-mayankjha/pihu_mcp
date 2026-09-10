import pytest
import json
from pihu.events.types import AgentEvent, EventType
from pihu.events.bus import EventBus

@pytest.mark.asyncio
async def test_agent_event_serialization():
    event = AgentEvent(
        type=EventType.TASK_STARTED,
        task_id="task_123",
        status="info",
        message="Started task",
        details={"foo": "bar"}
    )
    dumped = event.model_dump_json()
    parsed = json.loads(dumped)

    assert parsed["type"] == "TASK_STARTED"
    assert parsed["task_id"] == "task_123"
    assert parsed["details"]["foo"] == "bar"

@pytest.mark.asyncio
async def test_event_bus_subscribe():
    bus = EventBus(emit_to_stdout=False)
    received_events = []

    async def listener(event: AgentEvent):
        received_events.append(event)

    bus.subscribe(listener)
    event = AgentEvent(type=EventType.PLAN_CREATED, message="Plan created")
    await bus.emit(event)

    assert len(received_events) == 1
    assert received_events[0].type == EventType.PLAN_CREATED
