import os
import httpx
import uuid
from typing import List, Optional, Dict, Any
from pihu.llm.base import LLMProvider, LLMResponse, Message, ToolDefinition, ToolCall
from pihu.config.settings import settings


class GeminiProvider(LLMProvider):
    """Google Gemini cloud LLM provider implementation."""

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.default_model = default_model or settings.gemini_model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def name(self) -> str:
        return "gemini"

    async def is_available(self) -> bool:
        return bool(self.api_key)

    async def list_models(self) -> List[Dict[str, Any]]:
        """Dynamically query the Gemini API for available models."""
        if not self.api_key:
            return []
        try:
            url = f"{self.base_url}/models?key={self.api_key}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []
                data = resp.json()

            skip_keywords = {"preview", "tts", "image", "transcribe",
                             "embedding", "nano", "banana", "omni",
                             "gemma", "custom"}
            models = []
            for m in data.get("models", []):
                raw_name = m.get("name", "")
                name = raw_name.replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])

                if "generateContent" not in methods:
                    continue

                name_lower = name.lower()
                if any(kw in name_lower for kw in skip_keywords):
                    continue

                if not name.startswith("gemini"):
                    continue

                display = m.get("displayName", name)
                models.append({
                    "name": name,
                    "description": display,
                    "type": "cloud",
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
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        target_model = model or self.default_model

        contents = []
        system_instruction = None

        for m in messages:
            if m.role == "system":
                system_instruction = {"parts": [{"text": m.content or ""}]}
            elif m.role == "user":
                contents.append({"role": "user", "parts": [{"text": m.content or ""}]})
            elif m.role in {"assistant", "model"}:
                if m.raw_parts:
                    # Preserve exact model response parts (includes thoughtSignature)
                    contents.append({"role": "model", "parts": m.raw_parts})
                else:
                    parts = []
                    if m.content:
                        parts.append({"text": m.content})
                    if m.tool_calls:
                        for tc in m.tool_calls:
                            parts.append({
                                "functionCall": {
                                    "name": tc.name,
                                    "args": tc.arguments
                                }
                            })
                    contents.append({"role": "model", "parts": parts})
            elif m.role == "tool":
                contents.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": m.name or "tool_response",
                            "response": {"output": m.content}
                        }
                    }]
                })

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature}
        }

        if system_instruction:
            payload["systemInstruction"] = system_instruction

        if tools:
            payload["tools"] = [{
                "functionDeclarations": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "parameters": _clean_schema(t.parameters),
                    }
                    for t in tools
                ]
            }]

        url = f"{self.base_url}/models/{target_model}:generateContent?key={self.api_key}"

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            return LLMResponse(content="", model=target_model, provider=self.name)

        first_cand = candidates[0]
        content_parts = first_cand.get("content", {}).get("parts", [])

        text_content = []
        tool_calls = []

        for part in content_parts:
            if "text" in part:
                text_content.append(part["text"])
            if "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append(
                    ToolCall(
                        id=f"call_{uuid.uuid4().hex[:8]}",
                        name=fc.get("name", ""),
                        arguments=fc.get("args", {})
                    )
                )

        combined_text = "\n".join(text_content) if text_content else None

        return LLMResponse(
            content=combined_text,
            tool_calls=tool_calls,
            model=target_model,
            provider=self.name,
            usage=data.get("usageMetadata", {}),
            raw_parts=content_parts,
        )


def _clean_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Strip JSON Schema fields that Gemini REST API doesn't accept."""
    if not schema:
        return {"type": "object", "properties": {}}

    cleaned = {}
    allowed_keys = {"type", "properties", "required", "description",
                    "enum", "items", "format", "nullable"}

    for k, v in schema.items():
        if k not in allowed_keys:
            continue
        if k == "properties" and isinstance(v, dict):
            cleaned[k] = {
                prop_name: _clean_schema(prop_val) if isinstance(prop_val, dict) else prop_val
                for prop_name, prop_val in v.items()
            }
        elif k == "items" and isinstance(v, dict):
            cleaned[k] = _clean_schema(v)
        else:
            cleaned[k] = v

    if "type" not in cleaned:
        cleaned["type"] = "object"

    return cleaned
