import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.types import AgentTask
from app.agents.browser import BrowserAgent


def _make_llm(response="Browser summary"):
    llm = MagicMock()
    llm.model = "test-model"
    llm.ask = AsyncMock(return_value=response)
    return llm


def _make_cs():
    cs = MagicMock()
    cs.log = MagicMock(return_value=0.001)
    return cs


def _make_search(urls=None):
    s = MagicMock()
    s.execute = AsyncMock(return_value=urls or ["https://example.com/1", "https://example.com/2"])
    return s


def _make_browser(text="Page text content"):
    b = MagicMock()
    b.execute = AsyncMock(return_value=text)
    return b


@pytest.mark.asyncio
async def test_browser_agent_returns_result():
    agent = BrowserAgent(
        llm=_make_llm("AI news summary"),
        cost_service=_make_cs(),
        search_tool=_make_search(),
        browser_tool=_make_browser(),
    )
    task = AgentTask(task_id="t1", prompt="find latest AI security news")
    result = await agent.run(task)

    assert result.agent_name == "browser_agent"
    assert result.tokens_used > 0
    assert len(result.output) > 0


@pytest.mark.asyncio
async def test_browser_agent_calls_search():
    search = _make_search(["https://a.com"])
    agent = BrowserAgent(
        llm=_make_llm(),
        cost_service=_make_cs(),
        search_tool=search,
        browser_tool=_make_browser(),
    )
    task = AgentTask(task_id="t1", prompt="research quantum computing")
    await agent.run(task)

    search.execute.assert_called_once()


@pytest.mark.asyncio
async def test_browser_agent_logs_tokens():
    cs = _make_cs()
    agent = BrowserAgent(
        llm=_make_llm(),
        cost_service=cs,
        search_tool=_make_search(),
        browser_tool=_make_browser(),
    )
    task = AgentTask(task_id="t1", prompt="find AI news")
    await agent.run(task)

    cs.log.assert_called_once()
    args = cs.log.call_args[0]
    assert args[0] == "t1"
    assert args[1] == "browser_agent"


@pytest.mark.asyncio
async def test_browser_agent_handles_search_failure():
    search = MagicMock()
    search.execute = AsyncMock(side_effect=Exception("network error"))

    agent = BrowserAgent(
        llm=_make_llm(),
        cost_service=_make_cs(),
        search_tool=search,
        browser_tool=_make_browser(),
    )
    task = AgentTask(task_id="t1", prompt="find AI news")
    result = await agent.run(task)

    assert result.agent_name == "browser_agent"
    assert result.tokens_used == 0
