import re
from pathlib import Path

from app.agents.types import AgentResult, AgentStep, AgentTask
from app.cost_service import cost_service as _default_cs
from app.llm import LLM

_PATH_RE = re.compile(r"workspace/[\w./\-]+")


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text.split()) * 1.3))


def _extract_path(prompt: str) -> str:
    m = _PATH_RE.search(prompt)
    return m.group(0) if m else ""


class FileAgent:
    def __init__(self, llm: LLM = None, cost_service=None):
        self.llm = llm or LLM("smart_local")
        self._cs = cost_service if cost_service is not None else _default_cs

    async def run(self, task: AgentTask) -> AgentResult:
        file_path = task.context.get("file_path") or _extract_path(task.prompt)

        if not file_path:
            return AgentResult(
                task_id=task.task_id,
                agent_name="file_agent",
                output="No file path found in task.",
                tokens_used=0,
                steps=[AgentStep("Locate file", "error")],
            )

        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            return AgentResult(
                task_id=task.task_id,
                agent_name="file_agent",
                output=f"File not found: {file_path}",
                tokens_used=0,
                steps=[AgentStep(f"Read {file_path}", "error")],
            )

        prompt_text = f"{task.prompt}\n\nFile content:\n{content[:8000]}"
        response = await self.llm.ask(
            [{"role": "user", "content": prompt_text}],
            stream=False,
        )

        input_tokens = _estimate_tokens(prompt_text)
        output_tokens = _estimate_tokens(response)
        self._cs.log(task.task_id, "file_agent", self.llm.model, input_tokens, output_tokens)

        return AgentResult(
            task_id=task.task_id,
            agent_name="file_agent",
            output=response,
            tokens_used=input_tokens + output_tokens,
            steps=[
                AgentStep(f"Read {Path(file_path).name}", "done"),
                AgentStep("Analyze content", "done"),
            ],
        )
