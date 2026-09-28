import os
import asyncio
import httpx
import json
import uuid
from typing import List, Optional, Dict, Any
from pathlib import Path
from pihu.llm.base import LLMProvider, LLMResponse, Message, ToolDefinition, ToolCall
from pihu.config.settings import settings
from pihu.events.bus import bus
from pihu.events.types import EventType, AgentEvent


def discover_gemini_tokens() -> List[str]:
    """
    PIHU Token Protocol:
    Discovers all Gemini API tokens across environment variables, .env files,
    and ~/.pihu-os/config.json / ~/.pihu/config.json.
    """
    tokens = []

    def add_token(t: str):
        if not t:
            return
        t = t.strip().strip('"').strip("'")
        if t and t not in tokens and (t.startswith("AIzaSy") or len(t) > 20):
            tokens.append(t)

    # 1. Environment variables (scan all matching *GEMINI* or *PIHU*KEY*)
    for k, v in os.environ.items():
        k_upper = k.upper()
        if (
            ("GEMINI" in k_upper and "KEY" in k_upper)
            or ("GEMINI" in k_upper and "TOKEN" in k_upper)
            or ("PIHU" in k_upper and "KEY" in k_upper)
            or ("GOOGLE" in k_upper and "KEY" in k_upper)
        ):
            if "," in v:
                for part in v.split(","):
                    add_token(part)
            else:
                add_token(v)

    # Direct common env vars
    for env_var in [
        "PIHU_GEMINI_API_KEY",
        "PIHU_GEMINI_API_KEY2",
        "PIHU_GEMINI_API_KEY3",
        "PIHU_GEMINI_API_KEY4",
        "PIHU_GEMINI_KEY_1",
        "PIHU_GEMINI_KEY_2",
        "PIHU_GEMINI_KEY_3",
        "GEMINI_API_KEY",
        "GEMINI_API_KEY_1",
        "GEMINI_API_KEY_2",
        "GEMINI_API_KEY_3",
        "GOOGLE_API_KEY",
    ]:
        val = os.getenv(env_var, "").strip()
        add_token(val)

    # Pools
    for pool_var in ["VITE_GEMINI_API_KEYS", "GEMINI_API_KEYS", "PIHU_GEMINI_API_KEYS"]:
        pool_str = os.getenv(pool_var, "")
        if pool_str:
            for k in pool_str.split(","):
                add_token(k)

    # Settings fallback
    if settings.gemini_api_key:
        add_token(settings.gemini_api_key)

    # 2. Check .env files in local, parent, and home directories
    cwd = Path.cwd()
    env_paths = [
        cwd / ".env",
        cwd / ".." / ".env",
        cwd / ".." / ".." / ".env",
        Path.home() / ".pihu" / ".env",
        Path.home() / ".pihu-os" / ".env",
    ]
    for env_path in env_paths:
        try:
            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k_upper = k.strip().upper()
                        v = v.strip().strip('"').strip("'")
                        if (
                            ("GEMINI" in k_upper and ("KEY" in k_upper or "TOKEN" in k_upper))
                            or ("PIHU" in k_upper and "KEY" in k_upper)
                            or ("GOOGLE" in k_upper and "KEY" in k_upper)
                        ):
                            for part in v.split(","):
                                add_token(part)
        except Exception:
            pass

    # 3. Check ~/.pihu-os/config.json & ~/.pihu/config.json
    for cfg_path in [Path.home() / ".pihu-os" / "config.json", Path.home() / ".pihu" / "config.json"]:
        try:
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    keys = cfg.get("gemini", {}).get("api_keys", [])
                    for k in keys:
                        add_token(k)
        except Exception:
            pass

    return tokens


class GeminiProvider(LLMProvider):
    """Google Gemini cloud LLM provider implementation with PIHU Token Protocol rotation."""

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self._custom_api_key = api_key
        self.default_model = default_model or settings.gemini_model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self._key_index = 0

    @property
    def keys_pool(self) -> List[str]:
        if self._custom_api_key:
            return [self._custom_api_key]
        return discover_gemini_tokens()

    @property
    def api_key(self) -> str:
        pool = self.keys_pool
        if not pool:
            return ""
        return pool[self._key_index % len(pool)]

    def rotate_key(self) -> str:
        pool = self.keys_pool
        if len(pool) > 1:
            self._key_index = (self._key_index + 1) % len(pool)
        return self.api_key

    @property
    def name(self) -> str:
        return "gemini"

    async def is_available(self) -> bool:
        return bool(self.keys_pool)

    async def list_models(self) -> List[Dict[str, Any]]:
        """Dynamically query the Gemini API for available models."""
        pool = self.keys_pool
        if not pool:
            return []

        for key in pool:
            try:
                url = f"{self.base_url}/models?key={key}"
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                    data = resp.json()

                skip_keywords = {
                    "preview", "tts", "image", "transcribe",
                    "embedding", "nano", "banana", "omni",
                    "gemma", "custom"
                }
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

                if models:
                    return models
            except Exception:
                continue
        return []

    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        pool = self.keys_pool
        if not pool:
            raise ValueError(
                "Gemini API key is not configured.\n"
                "Please set your key using /key <TOKEN> or configure in .env / ~/.pihu-os/config.json"
            )

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
                                    "args": tc.arguments,
                                }
                            })
                    contents.append({"role": "model", "parts": parts})
            elif m.role == "tool":
                contents.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": m.name or "tool_response",
                            "response": {"output": m.content},
                        }
                    }],
                })

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
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

        last_error = None
        # 1. Primary pass: rotate through all keys in the pool
        for attempt in range(len(pool)):
            active_key = self.api_key
            url = f"{self.base_url}/models/{target_model}:generateContent?key={active_key}"

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(url, json=payload)

                    if resp.status_code == 404:
                        raise ValueError(
                            f"Model '{target_model}' was not found (HTTP 404). "
                            "Please choose a supported model using /model (e.g. gemini-2.0-flash)."
                        )

                    if resp.status_code in [429, 403, 500, 503]:
                        err_text = resp.text
                        last_error = f"HTTP {resp.status_code}: {err_text}"
                        self.rotate_key()
                        await bus.emit(AgentEvent(
                            type=EventType.MODEL_SWITCHED,
                            component="gemini_llm",
                            status="warning",
                            message=f"Gemini {target_model} returned HTTP {resp.status_code}. Rotating token ({self._key_index + 1}/{len(pool)})...",
                            details={"status": resp.status_code, "attempt": attempt + 1, "pool_size": len(pool)}
                        ))
                        await asyncio.sleep(0.5)
                        continue

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
                                    arguments=fc.get("args", {}),
                                )
                            )

                    return LLMResponse(
                        content="".join(text_content),
                        tool_calls=tool_calls or [],
                        model=target_model,
                        provider=self.name,
                        raw_parts=content_parts,
                    )

            except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as e:
                self.rotate_key()
                last_error = f"{type(e).__name__}: {str(e)}"
                await asyncio.sleep(0.5)
                continue

        # 2. Sibling Model Fallback on 503 High Demand or 429 across all keys
        fallback_models = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-pro-exp-02-05"]
        for fb_model in fallback_models:
            if fb_model == target_model:
                continue
            for fb_attempt in range(len(pool)):
                fb_key = self.api_key
                fb_url = f"{self.base_url}/models/{fb_model}:generateContent?key={fb_key}"
                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        fb_resp = await client.post(fb_url, json=payload)
                        if fb_resp.status_code == 200:
                            await bus.emit(AgentEvent(
                                type=EventType.MODEL_SWITCHED,
                                component="gemini_llm",
                                status="info",
                                message=f"Switched model {target_model} → {fb_model} (demand failover)",
                                details={"from": target_model, "to": fb_model}
                            ))
                            data = fb_resp.json()
                            candidates = data.get("candidates", [])
                            if not candidates:
                                return LLMResponse(content="", model=fb_model, provider=self.name)
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
                                            arguments=fc.get("args", {}),
                                        )
                                    )
                            return LLMResponse(
                                content="".join(text_content),
                                tool_calls=tool_calls or [],
                                model=fb_model,
                                provider=self.name,
                                raw_parts=content_parts,
                            )
                        else:
                            self.rotate_key()
                            await asyncio.sleep(0.3)
                except Exception:
                    self.rotate_key()
                    await asyncio.sleep(0.3)

        raise ValueError(
            f"All {len(pool)} Gemini token(s) failed or network unavailable: {last_error}\n\n"
            "Try: /key to switch/add tokens, /model to switch models, or /provider to use local Ollama"
        )


def _clean_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Clean JSON Schema for Google Gemini parameter specifications."""
    if not isinstance(schema, dict):
        return {}

    cleaned = {}
    for k, v in schema.items():
        if k in ["$schema", "additionalProperties", "title"]:
            continue
        if k == "properties" and isinstance(v, dict):
            cleaned[k] = {pk: _clean_schema(pv) for pk, pv in v.items()}
        elif k == "items" and isinstance(v, dict):
            cleaned[k] = _clean_schema(v)
        else:
            cleaned[k] = v

    if "type" not in cleaned:
        cleaned["type"] = "object"

    return cleaned
