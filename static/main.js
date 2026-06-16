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

document.addEventListener("htmx:afterSwap", () => {
  const feed = document.getElementById("task-feed");
  if (feed && feed.dataset.taskId) {
    connectSSE(feed.dataset.taskId);
  }
});

function connectSSE(taskId) {
  const feed = document.getElementById("feed");
  if (!feed) return;

  const source = new EventSource(`/tasks/${taskId}/events`);
  let activeLine = null;

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
    if (e.data) {
      const data = JSON.parse(e.data);
      appendLine(feed, data.message || "An error occurred.", "error");
    }
    source.close();
  });
}

function appendLine(feed, text, cssClass) {
  const line = document.createElement("div");
  line.className = `feed-line ${cssClass}`;
  line.textContent = text;
  feed.appendChild(line);
  return line;
}
