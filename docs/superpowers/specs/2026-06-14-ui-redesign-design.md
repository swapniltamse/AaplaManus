# AaplaManus v2 — Plan 3: UI Redesign Design

**Date:** 2026-06-14
**Status:** Design approved, pending implementation plan
**Repo:** https://github.com/swapniltamse/AaplaManus
**Branch:** v2/foundation

---

## Goal

Replace the inherited OpenManus HTML/JS with a clean HTMX-driven interface. Target audience: tech executives and non-technical users who are encountering local AI for the first time. The UI is a gateway — it must feel trustworthy, premium, and legible without requiring technical literacy.

---

## Design Decisions (from brainstorming)

| Screen | Decision |
|---|---|
| Home screen | Mission Dashboard — two-panel layout |
| Task running | Narrative Feed — plain-English sentence per event |
| Setup flow | Full-screen wizard, leads with value proposition |
| Cloud dialog | Privacy-First — "Data will leave this device" headline |
| Tooltips | Alpine.js toggle, hardcoded content |

---

## Architecture

**Tech stack:** HTMX 2.x (CDN), Jinja2 templates (already in FastAPI), Alpine.js 3.x (CDN, tooltips only), ~50 lines of vanilla JS (SSE connector only).

**File structure:**

```
templates/
  base.html                  # shared layout, HTMX + Alpine CDN, dark theme link
  index.html                 # home: two-panel dashboard
  partials/
    history.html             # left panel — recent missions list
    mission-input.html       # right panel — textarea + model indicator
    task-running.html        # narrative feed container
    task-complete.html       # final output card with copy button
    setup-wizard.html        # full-screen first-run overlay
    cloud-dialog.html        # privacy-first cloud approval modal

static/
  style.css                  # rewritten — dark theme, CSS custom properties, no inline styles
  main.js                    # ~50 lines: SSE connector + narrative line appender only
```

**New endpoints in `app.py`:**

```python
GET  /health/ollama          # 200 {"status":"ok"} or 503 {"status":"unavailable"}
GET  /partials/history       # renders partials/history.html — HTMX swap target
GET  /classify               # ?prompt=... → {"model": "Fast Local", "label": "Fast Local"} — drives model indicator
POST /tasks/cloud-approve    # accepts {task_id} — starts task on cloud model
```

`POST /tasks` gains a new response path: when SmartRouter sets `is_complex=True` and no cloud approval exists, returns HTTP 202 with:
```json
{"task_id": "...", "requires_approval": true, "estimated_cost": 0.04, "model": "gpt-4o"}
```
The response also sets `HX-Trigger: show-cloud-dialog` header so HTMX swaps in the cloud dialog partial automatically.

---

## Screens

### Home — Mission Dashboard

Two-panel layout. Left panel loads on page load via `hx-get="/partials/history" hx-trigger="load"`. Each history item shows: prompt text (truncated to 60 chars), agent names used, dollars saved. Right panel contains the mission input textarea with `hx-post="/tasks" hx-target="#right-panel" hx-swap="innerHTML"`. Model indicator below the textarea reads from SmartRouter classification on keyup (debounced 500ms). Each model label has a `[?]` tooltip.

### Task Running — Narrative Feed

Right panel swaps to `task-running.html` after task submission. Contains an empty `<div id="feed">` that JS populates via SSE. Each event appends a `<div class="feed-line {type}">`. Event-to-sentence mapping:

| SSE event type | Displayed sentence |
|---|---|
| `think` | "Manus is thinking through your request..." |
| `tool` | "Using a tool..." |
| `act` | "Taking action..." |
| `run` | The literal `result` field from the event |
| `complete` | Panel swaps to `task-complete.html` |
| `error` | Red feed line with the error message |

Done lines get `.done` class (checkmark prefix, gray text). Active line gets `.active` class (blinking cursor appended). Savings counter updates on each event from cumulative token count.

On `complete` event: JS calls `htmx.trigger("#history-panel", "refresh")` to reload the left panel. No full page reload.

### Setup Wizard — First Run

On page load, `hx-get="/health/ollama" hx-trigger="load" hx-target="#main-content" hx-swap="innerHTML"` fires. If Ollama returns 503, the response body is `setup-wizard.html` which replaces the entire main content area.

Wizard layout (full screen, centered):
1. Green status dot + "Local AI System" label
2. "AaplaManus" heading
3. Three stat blocks: $0 API Cost / 0 Data Sent Out / Runs on Your Hardware
4. One-sentence explanation of Ollama
5. "Download Ollama — Free" button (links to ollama.com)
6. "I installed it — continue" button → fires `hx-get="/health/ollama"` again

If the re-check returns 200, the wizard swaps out and the normal dashboard loads. If still 503, inline error: "Still not detected. Try restarting Ollama, then click again."

### Cloud Approval Dialog

Triggered by `HX-Trigger: show-cloud-dialog` response header from `POST /tasks`. HTMX swaps `cloud-dialog.html` into `#right-panel`.

Dialog elements:
- Amber dot + "Data will leave this device" headline
- Body: "Sending to {model}. Your prompt and any attached files will be processed on external servers."
- Cost row: "Estimated cost" / "$0.04"
- Primary button: "Approve and send to cloud" → `hx-post="/tasks/cloud-approve"`
- Secondary button: "Run locally instead" → re-submits with `force_local=true`

### Tooltips

`[?]` spans use `x-data="{ open: false }"` and `@click="open = !open"` (Alpine.js). Tooltip body is a sibling `<div x-show="open">` with hardcoded plain-English text. No server round-trip.

Tooltip copy:
- **Ollama** — "Runs AI on your computer so nothing is sent to the internet"
- **Agent** — "AI that takes actions, not just answers questions"
- **Fast Local** — "Quick answers. Great for summaries. Runs on your device."
- **Smart Local** — "More powerful. Best for research and complex tasks. Still local."
- **Code Expert** — "Specialized for writing and running code. Runs locally."
- **Cloud** — "Sends your request to an external AI service. Costs money. Your data leaves this device."

---

## Data Flow

```
User submits prompt
  → hx-post="/tasks"
  → FastAPI: SmartRouter classifies
    → if complex + no approval: return 202 + HX-Trigger: show-cloud-dialog
    → else: create task, start orchestrator, return 200 {task_id}
  → HTMX swaps right panel to task-running.html
  → main.js opens EventSource("/tasks/{task_id}/events")
  → each event: appendNarrativeLine(label, type)
  → on complete: htmx.trigger("#history-panel", "refresh")
```

SSE connector (full `main.js`):

```javascript
const LABELS = {
  think: "Manus is thinking through your request...",
  tool:  "Using a tool...",
  act:   "Taking action...",
};

function connectSSE(taskId) {
  const feed = document.getElementById("feed");
  const source = new EventSource(`/tasks/${taskId}/events`);

  source.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.type === "complete") {
      htmx.ajax("GET", `/tasks/${taskId}`, { target: "#right-panel", swap: "innerHTML" });
      htmx.trigger("#history-panel", "refresh");
      source.close();
      return;
    }
    const line = document.createElement("div");
    line.className = `feed-line ${data.type}`;
    line.textContent = LABELS[data.type] ?? data.result;
    feed.appendChild(line);
    feed.scrollTop = feed.scrollHeight;
  };

  source.onerror = () => source.close();
}
```

---

## Testing

**Target:** 8 new tests across 2 new test files. 42 existing tests must continue to pass.

**`tests/test_ui_routes.py`** (5 tests):
- `test_home_returns_htmx_form` — GET / contains `hx-post="/tasks"`
- `test_ollama_health_ok` — GET /health/ollama returns 200 when Ollama mock responds
- `test_ollama_health_unavailable` — GET /health/ollama returns 503 on timeout
- `test_complex_task_returns_202` — POST /tasks with complex prompt returns 202 + `requires_approval`
- `test_cloud_approve_starts_task` — POST /tasks/cloud-approve returns 200 with `task_id`

**`tests/test_templates.py`** (3 tests):
- `test_setup_wizard_contains_value_props` — setup-wizard.html contains "$0", "0 Data Sent Out", "Runs on Your Hardware"
- `test_cloud_dialog_privacy_language` — cloud-dialog.html contains "Data will leave this device" and "Approve and send to cloud"
- `test_history_partial_renders_savings` — /partials/history returns HTML with savings amount from CostService

---

## What is not in Plan 3

- Model pull progress bar (first Ollama model download) — Plan 4
- Desktop app packaging (Tauri) — Plan 6
- Mobile responsiveness — deferred
- Dark/light theme toggle — deferred
