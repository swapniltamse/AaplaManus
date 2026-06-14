from dataclasses import dataclass, field


@dataclass
class AgentStep:
    description: str
    status: str = "done"  # "pending", "running", "done", "error"


@dataclass
class AgentTask:
    task_id: str
    prompt: str
    context: dict = field(default_factory=dict)
    model: str = ""


@dataclass
class AgentResult:
    task_id: str
    agent_name: str
    output: str
    tokens_used: int
    steps: list = field(default_factory=list)  # list[AgentStep]
