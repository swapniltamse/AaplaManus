import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.types import AgentTask
from app.agents.code import CodeAgent


def _make_llm(responses=None):
    llm = MagicMock()
    llm.model = "test-model"
    if responses is None:
        responses = ["print('hello')"]
    llm.ask = AsyncMock(side_effect=responses if len(responses) > 1 else responses * 10)
    return llm


def _make_cs():
    cs = MagicMock()
    cs.log = MagicMock(return_value=0.001)
    return cs


def _make_executor(observation="hello", success=True):
    ex = MagicMock()
    result = {"observation": observation}
    if not success:
        result["success"] = False
    ex.execute = AsyncMock(return_value=result)
    return ex


@pytest.mark.asyncio
async def test_code_agent_success_first_try():
    agent = CodeAgent(
        llm=_make_llm(["print('hello')"]),
        cost_service=_make_cs(),
        executor=_make_executor("hello\n"),
    )
    task = AgentTask(task_id="t1", prompt="print hello world")
    result = await agent.run(task)

    assert result.agent_name == "code_agent"
    assert "hello" in result.output
    assert result.tokens_used > 0


@pytest.mark.asyncio
async def test_code_agent_retries_on_failure():
    executor = MagicMock()
    executor.execute = AsyncMock(side_effect=[
        {"observation": "NameError: x", "success": False},
        {"observation": "NameError: x", "success": False},
        {"observation": "42"},
    ])
    llm = _make_llm(["bad code", "fixed code v1", "fixed code v2"])

    agent = CodeAgent(llm=llm, cost_service=_make_cs(), executor=executor)
    task = AgentTask(task_id="t1", prompt="compute 6*7")
    result = await agent.run(task)

    assert executor.execute.call_count == 3
    assert "42" in result.output


@pytest.mark.asyncio
async def test_code_agent_strips_markdown_fences():
    from app.agents.code import _strip_code_fences
    fenced = "```python\nprint('hi')\n```"
    assert _strip_code_fences(fenced) == "print('hi')"


@pytest.mark.asyncio
async def test_code_agent_logs_tokens():
    cs = _make_cs()
    agent = CodeAgent(
        llm=_make_llm(["print('hi')"]),
        cost_service=cs,
        executor=_make_executor("hi"),
    )
    task = AgentTask(task_id="t2", prompt="say hi")
    await agent.run(task)

    cs.log.assert_called_once()
    args = cs.log.call_args[0]
    assert args[0] == "t2"
    assert args[1] == "code_agent"
