from app.agents.types import AgentTask, AgentResult, AgentStep


def test_agent_task_minimal():
    t = AgentTask(task_id="t1", prompt="hello")
    assert t.task_id == "t1"
    assert t.prompt == "hello"
    assert t.context == {}
    assert t.model == ""


def test_agent_task_with_context():
    t = AgentTask(task_id="t1", prompt="hello", context={"file_path": "/tmp/f.txt"}, model="qwen2.5:7b")
    assert t.context["file_path"] == "/tmp/f.txt"
    assert t.model == "qwen2.5:7b"


def test_agent_result_minimal():
    r = AgentResult(task_id="t1", agent_name="file_agent", output="text", tokens_used=100)
    assert r.task_id == "t1"
    assert r.agent_name == "file_agent"
    assert r.output == "text"
    assert r.tokens_used == 100
    assert r.steps == []


def test_agent_step_defaults():
    s = AgentStep(description="Reading file")
    assert s.description == "Reading file"
    assert s.status == "done"


def test_agent_step_custom_status():
    s = AgentStep(description="Searching", status="error")
    assert s.status == "error"


def test_agent_result_steps_isolation():
    r1 = AgentResult(task_id="t1", agent_name="agent1", output="out", tokens_used=50)
    r2 = AgentResult(task_id="t2", agent_name="agent2", output="out", tokens_used=50)
    r1.steps.append(AgentStep(description="step1"))
    assert len(r1.steps) == 1
    assert len(r2.steps) == 0


def test_agent_task_context_isolation():
    t1 = AgentTask(task_id="t1", prompt="hello")
    t2 = AgentTask(task_id="t2", prompt="world")
    t1.context["key"] = "value"
    assert "key" not in t2.context
