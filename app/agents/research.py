from app.agents.types import AgentResult, AgentStep, AgentTask
from app.cost_service import cost_service as _default_cs
from app.llm import LLM

_SYSTEM = (
    "You are a research analyst. Synthesize the provided information into a "
    "clear, accurate, and well-structured answer."
)

_MAX_SOURCE_CHARS = 12000


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text.split()) * 1.3))


class ResearchAgent:
    def __init__(self, llm: LLM = None, cost_service=None):
        self.llm = llm or LLM("smart_local")
        self._cs = cost_service if cost_service is not None else _default_cs

    async def run(self, task: AgentTask) -> AgentResult:
        prior_outputs = task.context.get("prior_outputs", [])

        if prior_outputs:
            source_block = "\n\n---\n\n".join(prior_outputs)
            user_content = f"{task.prompt}\n\nSources:\n{source_block[:_MAX_SOURCE_CHARS]}"
        else:
            user_content = task.prompt

        response = await self.llm.ask(
            [{"role": "user", "content": user_content}],
            system_msgs=[{"role": "system", "content": _SYSTEM}],
            stream=False,
        )

        input_tokens = _estimate_tokens(user_content)
        output_tokens = _estimate_tokens(response)
        self._cs.log(task.task_id, "research_agent", self.llm.model, input_tokens, output_tokens)

        return AgentResult(
            task_id=task.task_id,
            agent_name="research_agent",
            output=response,
            tokens_used=input_tokens + output_tokens,
            steps=[AgentStep("Synthesize sources", "done")],
        )
