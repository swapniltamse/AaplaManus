import os
import pytest

from app.cost_service import CostService


@pytest.fixture(autouse=True)
def fresh_service():
    os.environ["COST_DB_PATH"] = ":memory:"
    CostService._instance = None
    yield
    CostService._instance = None
    os.environ.pop("COST_DB_PATH", None)


def test_log_returns_correct_saved_amount():
    svc = CostService()
    saved = svc.log("session-1", "research_agent", "llama3.2:latest", 1000, 2000)
    # input:  (1000/1000) * 0.005 = 0.005
    # output: (2000/1000) * 0.015 = 0.030
    # total:  0.035
    assert abs(saved - 0.035) < 0.0001


def test_get_stats_alltime_totals():
    svc = CostService()
    svc.log("session-1", "file_agent", "llama3.2:latest", 500, 1000)
    svc.log("session-1", "research_agent", "llama3.2:latest", 500, 1000)
    stats = svc.get_stats()
    assert stats["alltime_saved_usd"] > 0
    assert stats["tasks_completed"] == 1  # 1 session


def test_get_stats_per_session():
    svc = CostService()
    svc.log("session-A", "file_agent", "llama3.2:latest", 1000, 1000)
    svc.log("session-B", "file_agent", "llama3.2:latest", 1000, 1000)
    stats_a = svc.get_stats(session_id="session-A")
    stats_b = svc.get_stats(session_id="session-B")
    assert stats_a["session_saved_usd"] > 0
    assert stats_b["session_saved_usd"] > 0
    assert abs(stats_a["session_saved_usd"] - stats_b["session_saved_usd"]) < 0.0001


def test_most_used_agent():
    svc = CostService()
    svc.log("s1", "research_agent", "llama3.2:latest", 100, 100)
    svc.log("s1", "research_agent", "llama3.2:latest", 100, 100)
    svc.log("s1", "file_agent", "llama3.2:latest", 100, 100)
    stats = svc.get_stats()
    assert stats["most_used_agent"] == "research_agent"
