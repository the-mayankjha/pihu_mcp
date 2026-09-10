import pytest
from unittest.mock import AsyncMock, patch
from pihu.llm.router import ModelRouter

@pytest.mark.asyncio
async def test_router_select_privacy_sensitive():
    router = ModelRouter()

    with patch.object(router.providers["ollama"], "is_available", new_callable=AsyncMock) as mock_ollama, \
         patch.object(router.providers["gemini"], "is_available", new_callable=AsyncMock) as mock_gemini:
        
        mock_ollama.return_value = True
        mock_gemini.return_value = True

        provider = await router.select_provider(
            task_prompt="Sensitive task",
            is_privacy_sensitive=True
        )
        assert provider.name == "ollama"

@pytest.mark.asyncio
async def test_router_select_complex_reasoning():
    router = ModelRouter()

    with patch.object(router.providers["ollama"], "is_available", new_callable=AsyncMock) as mock_ollama, \
         patch.object(router.providers["gemini"], "is_available", new_callable=AsyncMock) as mock_gemini:

        mock_ollama.return_value = True
        mock_gemini.return_value = True

        provider = await router.select_provider(
            task_prompt="Complex task",
            is_complex_reasoning=True
        )
        assert provider.name == "gemini"
