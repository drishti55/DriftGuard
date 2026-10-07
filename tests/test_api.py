"""
Tests for DriftGuard FastAPI endpoints.
Validates /api/health, /api/config, /api/stack, /api/delta, and /api/perception.
"""

from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "driftguard-api" in data["service"]


def test_api_config():
    res = client.get("/api/config")
    assert res.status_code == 200
    data = res.json()
    assert data["version"] == "1.0"
    assert "backend" in data["build_matrix"]["overrides"]


def test_api_stack():
    res = client.get("/api/stack")
    assert res.status_code == 200
    data = res.json()
    assert data["is_polyglot"] is True
    assert "Python" in data["detected_languages"]


def test_api_delta():
    res = client.get("/api/delta?base=HEAD~1")
    assert res.status_code == 200
    data = res.json()
    assert data["is_branch_targeted"] is True
    assert data["total_files_changed"] > 0


def test_api_perception():
    res = client.get("/api/perception?base=HEAD~1")
    assert res.status_code == 200
    data = res.json()
    assert data["audit_status"] == "READY_FOR_AUDIT"
    assert "effective_build_matrix" in data


def test_api_repositories():
    res = client.get("/api/repositories")
    assert res.status_code == 200
    data = res.json()
    assert "repositories" in data
    assert len(data["repositories"]) > 0

