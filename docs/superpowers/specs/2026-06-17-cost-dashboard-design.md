# Cost Dashboard — Real-Time Savings Counter Design

**Date:** 2026-06-17
**Status:** Approved
**Branch:** v2/foundation

---

## Goal

Wire the live savings counter in the task-running screen and add session stats (tasks completed, most used agent) to the history sidebar. Both use data already produced by `CostService` and already available at `GET /dashboard/stats`.

## Architecture

No new files. Three existing locations change:

- `static/main.js` — interval inside `connectSSE()` polls `/dashboard/stats?session_id=taskId` every 2s
- `templates/partials/history.html` — two new stat lines below the savings total
- `app.py` (`GET /partials/history`) — pass `tasks_completed` and `most_used_agent` to template

`CostService`, agents, and the SSE stream are untouched.

---

## Live Counter

`connectSSE(taskId)` in `main.js` starts an interval after registering SSE listeners:

```js
const statsInterval = setInterval(async () => {
  const r = await fetch(`/dashboard/stats?session_id=${taskId}`);
  const data = await r.json();
  const el = document.getElementById("savings-live");
  if (el) el.textContent = `Saved $${data.session_saved_usd.toFixed(2)} so far`;
}, 2000);
```

`clearInterval(statsInterval)` is added to both the `complete` handler and the `error` handler, before their existing HTMX swap calls. The interval is scoped inside `connectSSE` — no globals, no leaks between tasks.

The `#savings-live` div already exists in `task-running.html` with hardcoded `$0.00`. No template change needed for the counter.

---

## Sidebar Stats

`GET /partials/history` already calls `cost_service.get_stats()`. Pass the full result:

```python
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
```

`history.html` gains two lines below the existing savings total:

```html
<div class="savings-total">Saved ${{ "%.2f"|format(total_savings) }} total</div>
<div class="stat-line">{{ tasks_completed }} tasks completed</div>
{% if most_used_agent %}
<div class="stat-line">Most used: {{ most_used_agent }}</div>
{% endif %}
```

Stats refresh automatically after every mission because `htmx.trigger("#history-panel", "refresh")` already fires on task complete in `main.js`.

---

## Testing

3 new tests (50 existing + 3 = 53 total). All in `test_ui_routes.py`.

```python
def test_history_partial_includes_task_count(client):
    with patch.object(
        app_module._cost_service_module.cost_service,
        "get_stats",
        return_value={"alltime_saved_usd": 0.0, "tasks_completed": 5, "most_used_agent": None},
    ):
        response = client.get("/partials/history")
    assert "5 tasks completed" in response.text


def test_history_partial_includes_most_used_agent(client):
    with patch.object(
        app_module._cost_service_module.cost_service,
        "get_stats",
        return_value={"alltime_saved_usd": 0.0, "tasks_completed": 1, "most_used_agent": "research_agent"},
    ):
        response = client.get("/partials/history")
    assert "Most used: research_agent" in response.text


def test_dashboard_stats_session_savings_defaults_to_zero(client):
    response = client.get("/dashboard/stats?session_id=nonexistent-id")
    assert response.status_code == 200
    assert response.json()["session_saved_usd"] == 0.0
```

JS interval logic is not unit-tested. Coverage comes from the manual flow: run a task, watch the counter update. The endpoint the interval calls is already covered by existing tests.

---

## CSS

Add one rule to `style.css` for the new stat lines:

```css
.stat-line {
  font-size: 0.75rem;
  color: var(--muted, #64748b);
  margin-top: 0.25rem;
}
```

## What Is Not In Scope

- Alltime token count display
- Per-agent breakdown table
- WebSocket push (polling is sufficient at 2s cadence)
