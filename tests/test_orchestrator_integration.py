# tests/test_orchestrator_integration.py
import pytest
import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

# Explicitly load app.py module (not the app/ package)
app_path = Path(__file__).parent.parent / "app.py"
spec = importlib.util.spec_from_file_location("app_module", app_path)
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)


@pytest.fixture
def client():
    return TestClient(app_module.app)


@pytest.fixture(autouse=True)
def patch_orchestrator(monkeypatch):
    mock_orch = MagicMock()
    mock_orch.run = AsyncMock(return_value="Orchestrated result")
    monkeypatch.setattr(app_module, "_orchestrator", mock_orch)
    return mock_orch


def test_post_task_uses_orchestrator(client, patch_orchestrator):
    response = client.post("/tasks", json={"prompt": "test mission"})
    assert response.status_code == 200
    assert "task_id" in response.json()
