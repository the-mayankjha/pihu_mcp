import httpx
import json
import re
import uuid
from typing import List, Optional, Dict, Any
from pihu.llm.base import LLMProvider, LLMResponse, Message, ToolDefinition, ToolCall
from pihu.config.settings import settings

class OllamaProvider(LLMProvider):
    """Ollama local LLM provider implementation."""

    def __init__(self, base_url: Optional[str] = None, default_model: Optional[str] = None):
        self.base_url = base_url or settings.ollama_base_url
        self.default_model = default_model or settings.ollama_model

    @property
    def name(self) -> str:
        return "ollama"

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code != 200:
                    return False
                models = [m.get("name") for m in resp.json().get("models", [])]
                if not models:
                    return False
                return True
        except Exception:
            return False

    async def list_models(self) -> List[Dict[str, Any]]:
        """Query Ollama for all locally available models."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code != 200:
                    return []
                data = resp.json()
                models = []
                for m in data.get("models", []):
                    name = m.get("name", "")
                    size_bytes = m.get("size", 0)
                    size_gb = round(size_bytes / (1024**3), 1) if size_bytes else 0
                    param_size = m.get("details", {}).get("parameter_size", "")
                    family = m.get("details", {}).get("family", "")
                    models.append({
                        "name": name,
                        "size_gb": size_gb,
                        "parameter_size": param_size,
                        "family": family,
                    })
                return models
        except Exception:
            return []

    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        target_model = model or self.default_model

        # Format messages for Ollama API
        formatted_messages = []
        for m in messages:
            msg_dict: Dict[str, Any] = {"role": m.role, "content": m.content or ""}
            if m.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments
                        }
                    }
                    for tc in m.tool_calls
                ]
            formatted_messages.append(msg_dict)

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": formatted_messages,
            "stream": False,
            "options": {"temperature": temperature}
        }

        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    }
                }
                for t in tools
            ]

        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            
            # Fallback for models like gemma3:4b that do not support native tools parameter in Ollama
            if resp.status_code == 400 and "tools" in payload:
                payload_no_tools = dict(payload)
                del payload_no_tools["tools"]
                
                # Append tool descriptions to system prompt or first message
                if tools and payload_no_tools["messages"]:
                    tool_desc_text = "\n\nAvailable tools:\n" + "\n".join(
                        f"- {t.name}: {t.description}" for t in tools[:15]
                    )
                    payload_no_tools["messages"][0]["content"] += tool_desc_text

                resp = await client.post(f"{self.base_url}/api/chat", json=payload_no_tools)

            resp.raise_for_status()
            data = resp.json()

        message_data = data.get("message", {})
        content = message_data.get("content")
        tool_calls = []

        if "tool_calls" in message_data and message_data["tool_calls"]:
            for tc in message_data["tool_calls"]:
                func = tc.get("function", {})
                args = func.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                tool_calls.append(
                    ToolCall(
                        id=f"call_{uuid.uuid4().hex[:8]}",
                        name=func.get("name", ""),
                        arguments=args
                    )
                )

        # Fallback: Parse <function-call> XML tags if Ollama returned text tool calls
        if not tool_calls and content and "<function-call>" in content:
            matches = re.findall(r'<function-call>\s*(\{.*?\})\s*</function-call>', content, re.DOTALL)
            for m in matches:
                try:
                    fn_data = json.loads(m)
                    fn_name = fn_data.get("name")
                    fn_args = fn_data.get("arguments", {})
                    if fn_name:
                        tool_calls.append(
                            ToolCall(
                                id=f"call_{uuid.uuid4().hex[:8]}",
                                name=fn_name,
                                arguments=fn_args
                            )
                        )
                except Exception:
                    pass
            if tool_calls:
                content = re.sub(r'<function-call>\s*\{.*?\}\s*</function-call>', '', content, flags=re.DOTALL).strip()
                if not content:
                    content = None

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            model=target_model,
            provider=self.name,
            usage={
                "prompt_eval_count": data.get("prompt_eval_count", 0),
                "eval_count": data.get("eval_count", 0),
            }
        )
