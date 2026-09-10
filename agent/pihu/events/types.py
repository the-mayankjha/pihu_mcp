from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class EventType(str, Enum):
    TASK_STARTED = "TASK_STARTED"
    UNDERSTANDING = "UNDERSTANDING"
    CONTEXT_LOADING = "CONTEXT_LOADING"
    MODEL_SELECTED = "MODEL_SELECTED"
    MODEL_SWITCHED = "MODEL_SWITCHED"
    PLAN_CREATED = "PLAN_CREATED"
    TOOL_DISCOVERED = "TOOL_DISCOVERED"
    TOOL_STARTED = "TOOL_STARTED"
    TOOL_PROGRESS = "TOOL_PROGRESS"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    PERMISSION_REQUIRED = "PERMISSION_REQUIRED"
    PERMISSION_RESPONSE = "PERMISSION_RESPONSE"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    VERIFICATION_STARTED = "VERIFICATION_STARTED"
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    MEMORY_UPDATED = "MEMORY_UPDATED"
    ERROR = "ERROR"
    TASK_COMPLETED = "TASK_COMPLETED"

class AgentEvent(BaseModel):
    """Structured, serializable event sent between Python agent runtime and listeners/Go CLI."""
    type: EventType
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    component: str = "agent"
    status: str = "info"  # "info", "running", "success", "warning", "error", "pending"
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
