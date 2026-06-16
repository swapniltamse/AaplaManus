# tests/test_ui_routes.py
import importlib.util
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

app_path = Path(__file__).parent.parent / "app.py"
spec_obj = importlib.util.spec_from_file_location("app_module", app_path)
app_module = importlib.util.module_from_spec(spec_obj)
spec_obj.loader.exec_module(app_module)

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app_module.app)


def test_home_returns_htmx_form(client):
    with patch.object(app_module, "_check_ollama", new=AsyncMock(return_value=True)):
        response = client.get("/")
    assert response.status_code == 200
    assert 'hx-get="/partials/history"' in response.text
    assert 'id="mission-form"' in response.text


def test_ollama_health_ok(client):
    with patch.object(app_module, "_check_ollama", new=AsyncMock(return_value=True)):
        response = client.get("/health/ollama")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ollama_health_unavailable(client):
    with patch.object(app_module, "_check_ollama", new=AsyncMock(return_value=False)):
        response = client.get("/health/ollama")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"


def test_complex_task_returns_approval_info(client):
    # > 80 words triggers is_complex in classify()
    long_prompt = "research " + "word " * 82
    response = client.post("/tasks", json={"prompt": long_prompt})
    assert response.status_code == 200
    data = response.json()
    assert data["requires_approval"] is True
    assert "estimated_cost" in data
    assert "task_id" in data


def test_cloud_approve_starts_task(client):
    long_prompt = "research " + "word " * 82
    create_resp = client.post("/tasks", json={"prompt": long_prompt})
    task_id = create_resp.json()["task_id"]

    response = client.post("/tasks/cloud-approve", json={"task_id": task_id})
    assert response.status_code == 200
    assert task_id in response.text
