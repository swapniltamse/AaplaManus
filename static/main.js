const LABELS = {
  think: "Manus is thinking through your request...",
  tool:  "Using a tool...",
  act:   "Taking action...",
};

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("mission-form");
  if (!form) return;

  const promptInput = document.getElementById("prompt-input");
  const modelLabel  = document.getElementById("model-label");

  let debounceTimer;
  if (promptInput && modelLabel) {
    promptInput.addEventListener("input", () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(async () => {
        const prompt = promptInput.value.trim();
        if (!prompt) return;
        const res  = await fetch(`/classify?prompt=${encodeURIComponent(prompt)}`);
        const data = await res.json();
        modelLabel.textContent = data.label;
      }, 500);
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const prompt = promptInput ? promptInput.value.trim() : "";
    if (!prompt) return;

    const res  = await fetch("/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const data = await res.json();

    if (data.requires_approval) {
      htmx.ajax(
        "GET",
        `/partials/cloud-dialog?task_id=${data.task_id}&cost=${data.estimated_cost}&model=${data.model}`,
        { target: "#right-panel", swap: "innerHTML" }
      );
    } else {
      htmx.ajax(
        "GET",
        `/partials/task-running?task_id=${data.task_id}`,
        { target: "#right-panel", swap: "innerHTML" }
      );
    }
  });
});

let _cleanupSSE = null;

document.addEventListener("htmx:afterSwap", () => {
  if (_cleanupSSE) { _cleanupSSE(); _cleanupSSE = null; }
  const feed = document.getElementById("task-feed");
  if (feed && feed.dataset.taskId) {
    _cleanupSSE = connectSSE(feed.dataset.taskId);
  }
});

function connectSSE(taskId) {
  const feed = document.getElementById("feed");
  if (!feed) return;

  const source = new EventSource(`/tasks/${taskId}/events`);
  let activeLine = null;

  const statsInterval = setInterval(async () => {
    try {
      const r = await fetch(`/dashboard/stats?session_id=${taskId}`);
      const data = await r.json();
      const el = document.getElementById("savings-live");
      const val = typeof data.session_saved_usd === "number" ? data.session_saved_usd : 0;
      if (el) el.textContent = `Saved $${val.toFixed(2)} so far`;
    } catch (_) {}
  }, 2000);

  // Server sends explicit `event:` names (think/tool/act/run/step/complete/error),
  // so onmessage never fires — EventSource only invokes it for unnamed "message" events.
  const handleStep = (e) => {
    const data = JSON.parse(e.data);
    if (activeLine) {
      activeLine.classList.remove("active");
      activeLine.classList.add("done");
    }
    activeLine = appendLine(feed, LABELS[data.type] ?? data.result, "active");
    feed.scrollTop = feed.scrollHeight;
  };
  ["think", "tool", "act", "run", "step"].forEach((type) => {
    source.addEventListener(type, handleStep);
  });

  source.addEventListener("complete", () => {
    clearInterval(statsInterval);
    source.close();
    htmx.ajax("GET", `/partials/task-complete?task_id=${taskId}`, {
      target: "#right-panel",
      swap: "innerHTML",
    });
    htmx.trigger("#history-panel", "refresh");
  });

  // "error" fires both for the server's named error event (has e.data) and for
  // native connection failures (no e.data) — EventSource treats both as the same type.
  source.addEventListener("error", (e) => {
    clearInterval(statsInterval);
    if (e.data) {
      const data = JSON.parse(e.data);
      appendLine(feed, data.message || "An error occurred.", "error");
    }
    source.close();
  });

  return () => { clearInterval(statsInterval); source.close(); };
}

function appendLine(feed, text, cssClass) {
  const line = document.createElement("div");
  line.className = `feed-line ${cssClass}`;
  line.textContent = text;
  feed.appendChild(line);
  return line;
}
