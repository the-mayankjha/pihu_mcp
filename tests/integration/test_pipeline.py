import pytest
from unittest.mock import AsyncMock, patch
from pihu.agent.orchestrator import PihuAgent
from pihu.llm.base import LLMResponse

@pytest.mark.asyncio
async def test_agent_run_task_simple():
    agent = PihuAgent()

    # Mock router generate response
    mock_resp = LLMResponse(
        content="The time in Tokyo is 10:42 PM.",
        model="mock_model",
        provider="mock_provider"
    )

    with patch.object(agent.router, "generate", new_callable=AsyncMock) as mock_generate, \
         patch.object(agent.mcp_manager, "load_and_initialize", new_callable=AsyncMock) as mock_mcp_init, \
         patch.object(agent.mcp_manager, "close_all", new_callable=AsyncMock):

        mock_mcp_init.return_value = []
        mock_generate.return_value = mock_resp

        result = await agent.run_task("What time is it in Tokyo?")

        assert result == "The time in Tokyo is 10:42 PM."
        assert mock_generate.called
