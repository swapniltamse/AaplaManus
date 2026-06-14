from app.agents.types import AgentResult, AgentStep, AgentTask
from app.cost_service import cost_service as _default_cs
from app.llm import LLM
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.google_search import GoogleSearch

_MAX_PAGE_CHARS = 2000
_MAX_TOTAL_CHARS = 10000
_URLS_TO_FETCH = 2
_SEARCH_RESULTS = 5


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text.split()) * 1.3))


class BrowserAgent:
    def __init__(self, llm: LLM = None, cost_service=None, search_tool=None, browser_tool=None):
        self.llm = llm or LLM("smart_local")
        self._cs = cost_service if cost_service is not None else _default_cs
        self._search = search_tool or GoogleSearch()
        self._browser = browser_tool or BrowserUseTool()

    async def run(self, task: AgentTask) -> AgentResult:
        steps = []
        query = task.context.get("search_query", task.prompt)

        steps.append(AgentStep(f"Search: {query[:60]}", "running"))
        try:
            urls = await self._search.execute(query=query, num_results=_SEARCH_RESULTS)
            steps[-1] = AgentStep(f"Search: {query[:60]}", "done")
        except Exception as e:
            return AgentResult(
                task_id=task.task_id,
                agent_name="browser_agent",
                output=f"Search failed: {e}",
                tokens_used=0,
                steps=[AgentStep("Search", "error")],
            )

        collected = []
        for url in urls[:_URLS_TO_FETCH]:
            steps.append(AgentStep(f"Read {url}", "running"))
            try:
                await self._browser.execute(action="navigate", url=url)
                text = await self._browser.execute(action="get_text")
                collected.append(f"Source: {url}\n{str(text)[:_MAX_PAGE_CHARS]}")
                steps[-1] = AgentStep(f"Read {url}", "done")
            except Exception:
                steps[-1] = AgentStep(f"Read {url}", "error")

        raw_content = "\n\n".join(collected) if collected else "\n".join(urls)
        prompt_text = f"{task.prompt}\n\nWeb content:\n{raw_content[:_MAX_TOTAL_CHARS]}"

        steps.append(AgentStep("Summarize sources", "running"))
        response = await self.llm.ask(
            [{"role": "user", "content": prompt_text}],
            stream=False,
        )
        steps[-1] = AgentStep("Summarize sources", "done")

        input_tokens = _estimate_tokens(prompt_text)
        output_tokens = _estimate_tokens(response)
        self._cs.log(task.task_id, "browser_agent", self.llm.model, input_tokens, output_tokens)

        return AgentResult(
            task_id=task.task_id,
            agent_name="browser_agent",
            output=response,
            tokens_used=input_tokens + output_tokens,
            steps=steps,
        )
