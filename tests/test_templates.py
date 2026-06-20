# tests/test_templates.py
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


def test_setup_wizard_contains_value_props(client):
    with patch.object(app_module, "_check_ollama", new=AsyncMock(return_value=False)):
        response = client.get("/")
    assert response.status_code == 200
    assert "$0" in response.text
    assert "Data Sent Out" in response.text
    assert "Your HW" in response.text


def test_cloud_dialog_privacy_language(client):
    long_prompt = "research " + "word " * 82
    create_resp = client.post("/tasks", json={"prompt": long_prompt})
    task_id = create_resp.json()["task_id"]

    response = client.get(f"/partials/cloud-dialog?task_id={task_id}&cost=0.04&model=gpt-4o")
    assert response.status_code == 200
    assert "Data will leave this device" in response.text
    assert "Approve and send to cloud" in response.text


def test_history_partial_renders(client):
    with patch.object(
        app_module._cost_service_module.cost_service,
        "get_stats",
        return_value={"alltime_saved_usd": 1.23},
    ):
        response = client.get("/partials/history")
    assert response.status_code == 200
    assert "No missions" in response.text or "Saved $" in response.text
    assert "Saved $1.23 total" in response.text
