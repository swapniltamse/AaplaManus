import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.types import AgentResult, AgentStep, AgentTask
from app.orchestrator import Orchestrator


def _mock_agent(name, output):
    a = MagicMock()
    a.run = AsyncMock(return_value=AgentResult(
        task_id="t1", agent_name=name, output=output, tokens_used=100
    ))
    return a


@pytest.mark.asyncio
async def test_orchestrator_simple_task_uses_research_only():
    research = _mock_agent("research_agent", "What is FastAPI? It is a web framework.")
    orch = Orchestrator(
        research_agent=research,
        file_agent=_mock_agent("file_agent", ""),
        browser_agent=_mock_agent("browser_agent", ""),
        code_agent=_mock_agent("code_agent", ""),
    )

    result = await orch.run(task_id="t1", prompt="What is FastAPI?")

    assert result == "What is FastAPI? It is a web framework."
    research.run.assert_called_once()
    orch._file.run.assert_not_called()
    orch._browser.run.assert_not_called()
    orch._code.run.assert_not_called()


@pytest.mark.asyncio
async def test_orchestrator_browser_task_chains_to_research():
    browser = _mock_agent("browser_agent", "web content about AI security")
    research = _mock_agent("research_agent", "AI security synthesized")

    orch = Orchestrator(
        browser_agent=browser,
        research_agent=research,
        file_agent=_mock_agent("file_agent", ""),
        code_agent=_mock_agent("code_agent", ""),
    )

    result = await orch.run(task_id="t1", prompt="research latest AI security news")

    browser.run.assert_called_once()
    research.run.assert_called_once()
    research_task = research.run.call_args[0][0]
    assert "web content about AI security" in research_task.context.get("prior_outputs", [])
    assert result == "AI security synthesized"


@pytest.mark.asyncio
async def test_orchestrator_code_task_chains_to_research():
    code = _mock_agent("code_agent", "Code:\n```\nprint('hi')\n```\nOutput: hi")
    research = _mock_agent("research_agent", "synthesis")

    orch = Orchestrator(
        code_agent=code,
        research_agent=research,
        file_agent=_mock_agent("file_agent", ""),
        browser_agent=_mock_agent("browser_agent", ""),
    )

    result = await orch.run(task_id="t1", prompt="write a python script to add 2+2")

    code.run.assert_called_once()
    research_task = research.run.call_args[0][0]
    assert len(research_task.context.get("prior_outputs", [])) > 0


@pytest.mark.asyncio
async def test_orchestrator_passes_task_id_through():
    research = _mock_agent("research_agent", "answer")

    orch = Orchestrator(
        research_agent=research,
        file_agent=_mock_agent("file_agent", ""),
        browser_agent=_mock_agent("browser_agent", ""),
        code_agent=_mock_agent("code_agent", ""),
    )

    await orch.run(task_id="custom-uuid-123", prompt="hello")

    research_task = research.run.call_args[0][0]
    assert research_task.task_id == "custom-uuid-123"
