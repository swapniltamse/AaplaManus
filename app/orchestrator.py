from app.agents.browser import BrowserAgent
from app.agents.code import CodeAgent
from app.agents.file import FileAgent
from app.agents.research import ResearchAgent
from app.agents.types import AgentTask
from app.cost_service import cost_service as _default_cs
from app.router import classify


class Orchestrator:
    def __init__(
        self,
        cost_service=None,
        file_agent=None,
        browser_agent=None,
        code_agent=None,
        research_agent=None,
    ):
        cs = cost_service if cost_service is not None else _default_cs
        self._file = file_agent or FileAgent(cost_service=cs)
        self._browser = browser_agent or BrowserAgent(cost_service=cs)
        self._code = code_agent or CodeAgent(cost_service=cs)
        self._research = research_agent or ResearchAgent(cost_service=cs)

    async def run(self, task_id: str, prompt: str) -> str:
        route = classify(prompt)
        task = AgentTask(task_id=task_id, prompt=prompt, model=route.model_name)

        prior_outputs = []

        if route.needs_file:
            result = await self._file.run(task)
            prior_outputs.append(result.output)

        if route.needs_browser:
            result = await self._browser.run(task)
            prior_outputs.append(result.output)

        if route.needs_code:
            result = await self._code.run(task)
            prior_outputs.append(result.output)

        if prior_outputs:
            research_task = AgentTask(
                task_id=task_id,
                prompt=prompt,
                context={"prior_outputs": prior_outputs},
                model=route.model_name,
            )
            final = await self._research.run(research_task)
        else:
            final = await self._research.run(task)

        return final.output
