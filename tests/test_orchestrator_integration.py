import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.cost_service import CostService
import app.cost_service as cs_module


@pytest.fixture(autouse=True)
def reset_cost_service():
    os.environ["COST_DB_PATH"] = ":memory:"
    CostService._instance = None
    new_instance = CostService()
    cs_module.cost_service = new_instance
    yield
    cs_module.cost_service._conn.close()
    CostService._instance = None
    os.environ.pop("COST_DB_PATH", None)


@pytest.fixture
def client(monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("_app_module", "app.py")
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)

    # Patch the orchestrator after loading the module
    mock_orch = MagicMock()
    mock_orch.run = AsyncMock(return_value="Orchestrated result")
    monkeypatch.setattr(app_module, "_orchestrator", mock_orch)

    return TestClient(app_module.app), app_module, mock_orch


def test_post_task_uses_orchestrator(client):
    test_client, app_module, mock_orch = client
    response = test_client.post("/tasks", json={"prompt": "test mission"})
    assert response.status_code == 200
    assert "task_id" in response.json()
