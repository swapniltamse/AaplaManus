import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from app.agents.types import AgentTask
from app.agents.file import FileAgent


def _make_llm(response="LLM answer"):
    llm = MagicMock()
    llm.model = "test-model"
    llm.ask = AsyncMock(return_value=response)
    return llm


def _make_cs():
    cs = MagicMock()
    cs.log = MagicMock(return_value=0.001)
    return cs


@pytest.mark.asyncio
async def test_file_agent_reads_file_from_context(tmp_path):
    f = tmp_path / "report.txt"
    f.write_text("Revenue grew 20% this quarter.")

    llm = _make_llm("Summary: Revenue grew.")
    cs = _make_cs()

    agent = FileAgent(llm=llm, cost_service=cs)
    task = AgentTask(task_id="t1", prompt="Summarize this file", context={"file_path": str(f)})
    result = await agent.run(task)

    assert result.agent_name == "file_agent"
    assert "Revenue" in result.output or "Summary" in result.output
    assert result.tokens_used > 0
    cs.log.assert_called_once()


@pytest.mark.asyncio
async def test_file_agent_file_not_found():
    llm = _make_llm()
    cs = _make_cs()

    agent = FileAgent(llm=llm, cost_service=cs)
    task = AgentTask(task_id="t1", prompt="Summarize", context={"file_path": "/nonexistent/file.txt"})
    result = await agent.run(task)

    assert result.agent_name == "file_agent"
    assert "not found" in result.output.lower() or "error" in result.output.lower()
    assert result.tokens_used == 0
    cs.log.assert_not_called()


@pytest.mark.asyncio
async def test_file_agent_parses_path_from_prompt():
    from app.agents.file import _extract_path
    prompt = "analyze the file at workspace/data.csv please"
    assert _extract_path(prompt) == "workspace/data.csv"


@pytest.mark.asyncio
async def test_file_agent_no_path_returns_error():
    llm = _make_llm()
    cs = _make_cs()

    agent = FileAgent(llm=llm, cost_service=cs)
    task = AgentTask(task_id="t1", prompt="tell me something")
    result = await agent.run(task)

    assert result.agent_name == "file_agent"
    assert result.tokens_used == 0
    cs.log.assert_not_called()
