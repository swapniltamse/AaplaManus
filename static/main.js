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

  source.onmessage = (e) => {
    const data = JSON.parse(e.data);

    if (data.type === "complete") {
      source.close();
      htmx.ajax("GET", `/partials/task-complete?task_id=${taskId}`, {
        target: "#right-panel",
        swap: "innerHTML",
      });
      htmx.trigger("#history-panel", "refresh");
      return;
    }

    if (data.type === "error") {
      appendLine(feed, data.message || "An error occurred.", "error");
      source.close();
      return;
    }

    if (activeLine) {
      activeLine.classList.remove("active");
      activeLine.classList.add("done");
    }
    activeLine = appendLine(feed, LABELS[data.type] ?? data.result, "active");
    feed.scrollTop = feed.scrollHeight;
  };

  source.onerror = () => source.close();
}

function appendLine(feed, text, cssClass) {
  const line = document.createElement("div");
  line.className = `feed-line ${cssClass}`;
  line.textContent = text;
  feed.appendChild(line);
  return line;
}
