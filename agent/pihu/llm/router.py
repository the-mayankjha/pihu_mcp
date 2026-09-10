from typing import Dict, List, Optional, Any
from pihu.llm.base import LLMProvider, LLMResponse, Message, ToolDefinition
from pihu.llm.ollama import OllamaProvider
from pihu.llm.gemini import GeminiProvider
from pihu.config.settings import settings
from pihu.events.bus import bus
from pihu.events.types import AgentEvent, EventType

class ModelRouter:
    """Intelligent router selecting Ollama or Gemini based on availability, task attributes, and rules."""

    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {
            "ollama": OllamaProvider(),
            "gemini": GeminiProvider(),
        }

    async def discover_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """Discover all available models across all providers."""
        result = {}
        for name, provider in self.providers.items():
            try:
                models = await provider.list_models()
                if models:
                    result[name] = models
            except Exception:
                pass
        return result

    async def select_provider(
        self,
        task_prompt: str,
        is_privacy_sensitive: bool = False,
        is_complex_reasoning: bool = False,
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
    ) -> LLMProvider:
        # Infer provider from model name if provided
        if preferred_model:
            if preferred_model.startswith("gemini"):
                preferred_provider = "gemini"
            else:
                preferred_provider = "ollama"

        if preferred_provider and preferred_provider in self.providers:
            provider = self.providers[preferred_provider]
            if await provider.is_available():
                return provider
            else:
                raise RuntimeError(
                    f"LLM provider '{preferred_provider}' is not available. "
                    f"If using Ollama, ensure 'ollama serve' is running on {settings.ollama_base_url}."
                )

        # If privacy sensitive, prefer local Ollama
        if is_privacy_sensitive:
            ollama = self.providers["ollama"]
            if await ollama.is_available():
                return ollama

        # If complex reasoning, check Gemini
        if is_complex_reasoning:
            gemini = self.providers["gemini"]
            if await gemini.is_available():
                return gemini

        # Default fallback chain: Ollama -> Gemini
        ollama = self.providers["ollama"]
        if await ollama.is_available():
            return ollama

        gemini = self.providers["gemini"]
        if await gemini.is_available():
            return gemini

        raise RuntimeError("No available LLM providers configured or online (both Ollama and Gemini unavailable).")

    async def generate(
        self,
        task_prompt: str,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        is_privacy_sensitive: bool = False,
        is_complex_reasoning: bool = False,
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
    ) -> LLMResponse:
        provider = await self.select_provider(
            task_prompt=task_prompt,
            is_privacy_sensitive=is_privacy_sensitive,
            is_complex_reasoning=is_complex_reasoning,
            preferred_provider=preferred_provider,
            preferred_model=preferred_model,
        )

        selected_model = preferred_model or (settings.gemini_model if provider.name == "gemini" else settings.ollama_model)

        await bus.emit(
            AgentEvent(
                type=EventType.MODEL_SELECTED,
                component="model_router",
                status="info",
                message=f"Selected LLM provider: {provider.name} (model: {selected_model})",
                details={"provider": provider.name, "model": selected_model}
            )
        )

        try:
            return await provider.generate(messages=messages, tools=tools, model=preferred_model)
        except Exception as e:
            if preferred_provider or preferred_model:
                raise e

            fallback_name = "gemini" if provider.name == "ollama" else "ollama"
            fallback_provider = self.providers[fallback_name]
            if await fallback_provider.is_available():
                await bus.emit(
                    AgentEvent(
                        type=EventType.MODEL_SWITCHED,
                        component="model_router",
                        status="warning",
                        message=f"Primary provider {provider.name} failed ({str(e)}). Switching to fallback: {fallback_name}",
                        details={"from": provider.name, "to": fallback_name, "error": str(e)}
                    )
                )
                return await fallback_provider.generate(messages=messages, tools=tools)
            raise e
