import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.types import AgentTask
from app.agents.research import ResearchAgent


def _make_llm(response="Synthesized answer"):
    llm = MagicMock()
    llm.model = "test-model"
    llm.ask = AsyncMock(return_value=response)
    return llm


def _make_cs():
    cs = MagicMock()
    cs.log = MagicMock(return_value=0.001)
    return cs


@pytest.mark.asyncio
async def test_research_agent_simple_prompt():
    llm = _make_llm("FastAPI is a web framework.")
    cs = _make_cs()

    agent = ResearchAgent(llm=llm, cost_service=cs)
    task = AgentTask(task_id="t1", prompt="What is FastAPI?")
    result = await agent.run(task)

    assert result.agent_name == "research_agent"
    assert "FastAPI" in result.output
    assert result.tokens_used > 0
    cs.log.assert_called_once()


@pytest.mark.asyncio
async def test_research_agent_synthesizes_prior_outputs():
    llm = _make_llm("Combined answer.")
    cs = _make_cs()

    agent = ResearchAgent(llm=llm, cost_service=cs)
    task = AgentTask(
        task_id="t1",
        prompt="Summarize AI in finserv",
        context={"prior_outputs": ["Browser found X", "File said Y"]},
    )
    result = await agent.run(task)

    assert result.agent_name == "research_agent"
    call_args = llm.ask.call_args
    messages_sent = call_args[0][0]
    combined = " ".join(m["content"] for m in messages_sent if "content" in m)
    assert "Browser found X" in combined
    assert "File said Y" in combined


@pytest.mark.asyncio
async def test_research_agent_logs_tokens():
    llm = _make_llm("answer")
    cs = _make_cs()

    agent = ResearchAgent(llm=llm, cost_service=cs)
    task = AgentTask(task_id="t2", prompt="short question")
    await agent.run(task)

    cs.log.assert_called_once()
    args = cs.log.call_args[0]
    assert args[0] == "t2"
    assert args[1] == "research_agent"
