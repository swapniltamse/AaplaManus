import asyncio
import uuid
from datetime import datetime
from json import dumps
from typing import Optional

import httpx as _httpx

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Task(BaseModel):
    id: str
    prompt: str
    created_at: datetime
    status: str
    steps: list = []

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        data["created_at"] = self.created_at.isoformat()
        return data


class TaskManager:
    def __init__(self):
        self.tasks = {}
        self.queues = {}

    def create_task(self, prompt: str) -> Task:
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id, prompt=prompt, created_at=datetime.now(), status="pending"
        )
        self.tasks[task_id] = task
        self.queues[task_id] = asyncio.Queue()
        return task

    async def update_task_step(
        self, task_id: str, step: int, result: str, step_type: str = "step"
    ):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.steps.append({"step": step, "result": result, "type": step_type})
            await self.queues[task_id].put(
                {"type": step_type, "step": step, "result": result}
            )
            await self.queues[task_id].put(
                {"type": "status", "status": task.status, "steps": task.steps}
            )

    async def complete_task(self, task_id: str):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = "completed"
            await self.queues[task_id].put(
                {"type": "status", "status": task.status, "steps": task.steps}
            )
            await self.queues[task_id].put({"type": "complete"})

    async def fail_task(self, task_id: str, error: str):
        if task_id in self.tasks:
            self.tasks[task_id].status = f"failed: {error}"
            await self.queues[task_id].put({"type": "error", "message": error})


task_manager = TaskManager()


async def _check_ollama() -> bool:
    try:
        async with _httpx.AsyncClient() as c:
            r = await c.get("http://localhost:11434", timeout=2.0)
            return r.status_code < 500
    except Exception:
        return False


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    ollama_ok = await _check_ollama()
    return templates.TemplateResponse(
        "index.html", {"request": request, "ollama_ok": ollama_ok}
    )


@app.get("/health/ollama")
async def health_ollama():
    ok = await _check_ollama()
    if ok:
        return {"status": "ok"}
    return JSONResponse({"status": "unavailable"}, status_code=503)


@app.post("/tasks")
async def create_task(prompt: str = Body(..., embed=True)):
    from app.router import classify

    route = classify(prompt)
    task = task_manager.create_task(prompt)
    if route.is_complex:
        task_manager.tasks[task.id].status = "pending_approval"
        return {
            "task_id": task.id,
            "requires_approval": True,
            "estimated_cost": 0.04,
            "model": "gpt-4o",
        }
    asyncio.create_task(run_task(task.id, prompt))
    return {"task_id": task.id, "requires_approval": False}


import app.cost_service as _cost_service_module
from app.orchestrator import Orchestrator

_orchestrator = Orchestrator()


async def run_task(task_id: str, prompt: str):
    try:
        task_manager.tasks[task_id].status = "running"
        result = await _orchestrator.run(task_id=task_id, prompt=prompt)
        await task_manager.update_task_step(task_id, 1, result, "run")
        await task_manager.complete_task(task_id)
    except Exception as e:
        await task_manager.fail_task(task_id, str(e))


@app.get("/partials/history", response_class=HTMLResponse)
async def history_partial(request: Request):
    sorted_tasks = sorted(
        task_manager.tasks.values(), key=lambda t: t.created_at, reverse=True
    )
    stats = _cost_service_module.cost_service.get_stats()
    return templates.TemplateResponse(
        "partials/history.html",
        {
            "request": request,
            "tasks": sorted_tasks[:20],
            "total_savings": stats.get("alltime_saved_usd", 0.0),
            "tasks_completed": stats.get("tasks_completed", 0),
            "most_used_agent": stats.get("most_used_agent"),
        },
    )


@app.get("/partials/task-running", response_class=HTMLResponse)
async def task_running_partial(request: Request, task_id: str):
    return templates.TemplateResponse(
        "partials/task-running.html", {"request": request, "task_id": task_id}
    )


@app.get("/partials/task-complete", response_class=HTMLResponse)
async def task_complete_partial(request: Request, task_id: str):
    task = task_manager.tasks.get(task_id)
    output = ""
    if task and task.steps:
        for step in reversed(task.steps):
            if step.get("type") == "run":
                output = step.get("result", "")
                break
    return templates.TemplateResponse(
        "partials/task-complete.html", {"request": request, "output": output}
    )


@app.get("/partials/cloud-dialog", response_class=HTMLResponse)
async def cloud_dialog_partial(
    request: Request, task_id: str, cost: float = 0.04, model: str = "gpt-4o"
):
    return templates.TemplateResponse(
        "partials/cloud-dialog.html",
        {"request": request, "task_id": task_id, "estimated_cost": cost, "model": model},
    )


@app.get("/classify")
async def classify_prompt(prompt: str = ""):
    from app.router import classify, FAST_LOCAL, SMART_LOCAL, CODE_EXPERT

    LABEL_MAP = {
        FAST_LOCAL: "Fast Local",
        SMART_LOCAL: "Smart Local",
        CODE_EXPERT: "Code Expert",
    }
    route = classify(prompt)
    return {"model_key": route.model_key, "label": LABEL_MAP.get(route.model_key, "Cloud")}


@app.post("/tasks/cloud-approve", response_class=HTMLResponse)
async def cloud_approve(request: Request, task_id: str = Body(..., embed=True)):
    if task_id not in task_manager.tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    prompt = task_manager.tasks[task_id].prompt
    task_manager.tasks[task_id].status = "pending"
    asyncio.create_task(run_task(task_id, prompt))
    return templates.TemplateResponse(
        "partials/task-running.html", {"request": request, "task_id": task_id}
    )


@app.get("/tasks/{task_id}/events")
async def task_events(task_id: str):
    async def event_generator():
        if task_id not in task_manager.queues:
            yield f"event: error\ndata: {dumps({'message': 'Task not found'})}\n\n"
            return

        queue = task_manager.queues[task_id]

        task = task_manager.tasks.get(task_id)
        if task:
            yield f"event: status\ndata: {dumps({'type': 'status', 'status': task.status, 'steps': task.steps})}\n\n"

        while True:
            try:
                event = await queue.get()
                formatted_event = dumps(event)

                yield ": heartbeat\n\n"

                if event["type"] == "complete":
                    yield f"event: complete\ndata: {formatted_event}\n\n"
                    break
                elif event["type"] == "error":
                    yield f"event: error\ndata: {formatted_event}\n\n"
                    break
                elif event["type"] == "step":
                    task = task_manager.tasks.get(task_id)
                    if task:
                        yield f"event: status\ndata: {dumps({'type': 'status', 'status': task.status, 'steps': task.steps})}\n\n"
                    yield f"event: {event['type']}\ndata: {formatted_event}\n\n"
                elif event["type"] in ["think", "tool", "act", "run"]:
                    yield f"event: {event['type']}\ndata: {formatted_event}\n\n"
                else:
                    yield f"event: {event['type']}\ndata: {formatted_event}\n\n"

            except asyncio.CancelledError:
                print(f"Client disconnected for task {task_id}")
                break
            except Exception as e:
                print(f"Error in event stream: {str(e)}")
                yield f"event: error\ndata: {dumps({'message': str(e)})}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/tasks")
async def get_tasks():
    sorted_tasks = sorted(
        task_manager.tasks.values(), key=lambda task: task.created_at, reverse=True
    )
    return JSONResponse(
        content=[task.model_dump() for task in sorted_tasks],
        headers={"Content-Type": "application/json"},
    )


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    if task_id not in task_manager.tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_manager.tasks[task_id]


@app.get("/dashboard/stats")
async def get_dashboard_stats(session_id: Optional[str] = None):
    return _cost_service_module.cost_service.get_stats(session_id=session_id)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500, content={"message": f"Server error: {str(exc)}"}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=5172)
