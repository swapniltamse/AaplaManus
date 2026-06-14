from app.agents.types import AgentResult, AgentStep, AgentTask
from app.cost_service import cost_service as _default_cs
from app.llm import LLM
from app.tool.python_execute import PythonExecute

_MAX_RETRIES = 3


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text.split()) * 1.3))


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # remove ```python or ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines)
    return text


class CodeAgent:
    def __init__(self, llm: LLM = None, cost_service=None, executor=None):
        self.llm = llm or LLM("code_expert")
        self._cs = cost_service if cost_service is not None else _default_cs
        self._executor = executor or PythonExecute()

    async def run(self, task: AgentTask) -> AgentResult:
        steps = []

        code_prompt = (
            f"Write Python code to accomplish this task: {task.prompt}\n\n"
            "Return only the Python code with no explanation or markdown fences."
        )
        steps.append(AgentStep("Write code", "running"))
        code = _strip_code_fences(
            await self.llm.ask([{"role": "user", "content": code_prompt}], stream=False)
        )
        steps[-1] = AgentStep("Write code", "done")

        exec_result = {"observation": ""}
        for attempt in range(_MAX_RETRIES):
            steps.append(AgentStep(f"Run code (attempt {attempt + 1})", "running"))
            exec_result = await self._executor.execute(code=code)
            if exec_result.get("success") is not False:
                steps[-1] = AgentStep(f"Run code (attempt {attempt + 1})", "done")
                break
            steps[-1] = AgentStep(f"Run code (attempt {attempt + 1})", "error")
            if attempt < _MAX_RETRIES - 1:
                fix_prompt = (
                    f"This code failed with: {exec_result.get('observation', '')}\n\n"
                    f"Code:\n{code}\n\nFix it. Return only the corrected Python code."
                )
                code = _strip_code_fences(
                    await self.llm.ask([{"role": "user", "content": fix_prompt}], stream=False)
                )

        input_tokens = _estimate_tokens(code_prompt)
        output_tokens = _estimate_tokens(code)
        self._cs.log(task.task_id, "code_agent", self.llm.model, input_tokens, output_tokens)

        output = (
            f"Code:\n```python\n{code}\n```\n\n"
            f"Output:\n{exec_result.get('observation', '')}"
        )

        return AgentResult(
            task_id=task.task_id,
            agent_name="code_agent",
            output=output,
            tokens_used=input_tokens + output_tokens,
            steps=steps,
        )
