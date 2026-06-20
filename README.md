# AaplaManus

Local-first multi-agent AI system built on [Ollama](https://ollama.com). Run AI agents on your own hardware — no API keys, no monthly bill, no data leaving the machine.

> **Aapla Manus** is Marathi for "our person." The agent runs on your machine, answering to you.

Forked from [OpenManus](https://github.com/mannaandpoem/OpenManus) and rebuilt for local-first operation.

---

## What it does

AaplaManus gives you a set of agents — browser, code, research, file — that work together to complete tasks. Every run stays local by default. Cloud is an opt-in escape hatch, not the default.

**Three pillars:**
1. Agent tasks as the core — browse, code, research, read files
2. Cost savings as the hook — every session shows dollars saved vs GPT-4o
3. Smart routing — local by default, cloud only when you approve

---

## Architecture

```
User (Web UI)
    |
FastAPI + SSE (app.py)
    |
Orchestrator  →  SmartRouter (keyword classifier, no LLM call)
    |
[File Agent] [Browser Agent] [Code Agent] [Research Agent]
    |
Ollama (local LLM runtime, OpenAI-compatible API)
    |
Cost Service (SQLite, tracks tokens and savings per session)
```

**Model assignments:**

| Label | Model | Used for |
|---|---|---|
| Fast Local | qwen2.5:7b | Routing, simple tasks |
| Smart Local | llama3.2:latest | Research, synthesis |
| Code Expert | qwen2.5-coder:14b | Code generation |

---

## Agents

- **FileAgent** — reads files from the workspace, summarizes contents
- **BrowserAgent** — searches the web, fetches and extracts page text
- **CodeAgent** — writes and executes Python, retries up to 3x on failure
- **ResearchAgent** — synthesizes outputs from other agents into a final answer
- **Orchestrator** — routes the task, chains agents, returns the final result

---

## Getting started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [Ollama](https://ollama.com) (or let Docker pull it automatically)

### Run with Docker Compose

```bash
git clone https://github.com/swapniltamse/AaplaManus.git
cd AaplaManus
cp config/config.example.toml config/config.toml
docker compose up
```

App runs at `http://localhost:3000`.

Ollama starts automatically inside Docker. On first run, pull the models you want:

```bash
docker exec -it aaplamanus-ollama-1 ollama pull llama3.2
docker exec -it aaplamanus-ollama-1 ollama pull qwen2.5:7b
docker exec -it aaplamanus-ollama-1 ollama pull qwen2.5-coder:14b
```

### Run locally (without Docker)

```bash
git clone https://github.com/swapniltamse/AaplaManus.git
cd AaplaManus
cp config/config.example.toml config/config.toml

uv venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -r requirements.txt

uvicorn app:app --host 0.0.0.0 --port 3000
```

Requires Ollama running at `http://localhost:11434` (default).

---

## Configuration

`config/config.toml` (copy from `config.example.toml`):

```toml
[llm]
model = "llama3.2:latest"
base_url = "http://localhost:11434/v1"
api_key = "ollama"
max_tokens = 4096
temperature = 0.0
```

Set `OLLAMA_HOST` env var to override the Ollama URL (useful in Docker):

```bash
OLLAMA_HOST=http://ollama:11434
```

---

## Cost dashboard

Every agent call is tracked. Check your session savings:

```
GET /dashboard/stats
```

Returns total tokens used, estimated cost, and savings vs GPT-4o rates.

---

## Tests

```bash
.venv/Scripts/python.exe -m pytest tests/ -v   # Windows
python -m pytest tests/ -v                      # Linux/Mac
```

42 tests across types, agents, orchestrator, and integration.

---

## Roadmap

- [x] Plan 1: Ollama integration, Cost Service, Smart Router, Docker
- [x] Plan 2: File, Browser, Code, Research agents + Orchestrator
- [ ] Plan 3: UI redesign — TBD
- [ ] Plan 4: Setup flow and first-run experience — TBD
- [ ] Plan 5: Cloud approval dialog and opt-in routing — TBD
- [ ] Plan 6: Desktop app (Tauri) — TBD

---

## Acknowledgements

Built on [OpenManus](https://github.com/mannaandpoem/OpenManus) by the MetaGPT team.
Browser tooling via [browser-use](https://github.com/browser-use/browser-use).
