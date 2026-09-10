from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]

class Message(BaseModel):
    role: str  # "system", "user", "assistant", "tool"
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    raw_parts: Optional[List[Dict[str, Any]]] = None

class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

class LLMResponse(BaseModel):
    content: Optional[str] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)
    model: str
    provider: str
    usage: Dict[str, Any] = Field(default_factory=dict)
    raw_parts: Optional[List[Dict[str, Any]]] = None

class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider service is reachable."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate completion or tool call response."""
        pass
