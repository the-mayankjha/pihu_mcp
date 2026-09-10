from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class ExecutionState(str, Enum):
    RECEIVED = "RECEIVED"
    UNDERSTANDING = "UNDERSTANDING"
    CONTEXT_LOADING = "CONTEXT_LOADING"
    PLANNING = "PLANNING"
    MODEL_SELECTION = "MODEL_SELECTION"
    TOOL_SELECTION = "TOOL_SELECTION"
    PERMISSION_CHECK = "PERMISSION_CHECK"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    VERIFYING = "VERIFYING"
    MEMORY_UPDATE = "MEMORY_UPDATE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class TaskContext(BaseModel):
    task_id: str
    prompt: str
    state: ExecutionState = ExecutionState.RECEIVED
    metadata: Dict[str, Any] = Field(default_factory=dict)
