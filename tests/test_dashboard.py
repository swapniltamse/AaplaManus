import os
import pytest

from app.cost_service import CostService
import app.cost_service as cs_module

from fastapi.testclient import TestClient


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
def client():
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location("_app_module", "app.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return TestClient(mod.app)


def test_dashboard_stats_shape(client):
    response = client.get("/dashboard/stats")
    assert response.status_code == 200
    body = response.json()
    assert "session_saved_usd" in body
    assert "alltime_saved_usd" in body
    assert "alltime_tokens" in body
    assert "tasks_completed" in body
    assert "most_used_agent" in body


def test_dashboard_stats_reflects_logged_tokens(client):
    cs_module.cost_service.log("sess-1", "file_agent", "llama3.2:latest", 1000, 2000)
    response = client.get("/dashboard/stats")
    assert response.status_code == 200
    assert response.json()["alltime_saved_usd"] > 0


def test_dashboard_stats_session_filter(client):
    cs_module.cost_service.log("sess-A", "research_agent", "llama3.2:latest", 1000, 1000)
    cs_module.cost_service.log("sess-B", "file_agent", "llama3.2:latest", 1000, 1000)
    response = client.get("/dashboard/stats?session_id=sess-A")
    assert response.status_code == 200
    body = response.json()
    assert body["session_saved_usd"] > 0
