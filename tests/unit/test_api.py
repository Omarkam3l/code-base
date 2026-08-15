"""Unit tests for FastAPI REST API endpoints."""

from fastapi.testclient import TestClient
from codegraph.api.app import app

client = TestClient(app)


def test_api_health_check() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["data"]["status"] == "healthy"


def test_api_repository_registration_and_list() -> None:
    res = client.post("/repositories", json={"path": "examples/sample_project", "name": "API Test Repo"})
    assert res.status_code == 200
    reg = res.json()
    assert reg["status"] == "success"

    res_list = client.get("/repositories")
    assert res_list.status_code == 200
    assert len(res_list.json()["data"]) >= 1


def test_api_path_traversal_rejection() -> None:
    res = client.post("/repositories", json={"path": "../../../etc/passwd", "name": "Malicious Repo"})
    assert res.status_code == 400
    assert "Path traversal rejected" in res.json()["detail"]


def test_api_sensitive_system_path_rejected() -> None:
    """Absolute paths under sensitive system directories must be rejected even
    without literal '..' — the old blocklist only checked two hardcoded prefixes."""
    import platform
    if platform.system() == "Windows":
        res = client.post("/repositories", json={"path": "C:\\Windows\\System32", "name": "WinSys"})
        assert res.status_code == 400
        assert "forbidden" in res.json()["detail"].lower()

        res2 = client.post("/repositories", json={"path": "C:\\Users\\Administrator\\Desktop", "name": "AdminDesk"})
        assert res2.status_code == 400
    else:
        res = client.post("/repositories", json={"path": "/root/.ssh", "name": "SSH Keys"})
        assert res.status_code == 400
        assert "forbidden" in res.json()["detail"].lower()

        res2 = client.post("/repositories", json={"path": "/proc/self/environ", "name": "Proc Env"})
        assert res2.status_code == 400


def test_api_query_and_investigate() -> None:
    res_q = client.post("/query", json={"query": "UserService", "repository_id": "repository:sample_project"})
    assert res_q.status_code == 200

    res_inv = client.post("/investigate", json={"question": "Why auth failed?", "repository_id": "repository:sample_project"})
    assert res_inv.status_code == 200
    assert "investigation_id" in res_inv.json()["data"]
