"""Unit tests for CodeGraph Studio Web UI and static assets serving."""

from fastapi.testclient import TestClient
from codegraph.api.app import app


def test_studio_ui_root_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "CodeGraph Studio" in response.text
    assert "Knowledge Graph" in response.text


def test_studio_static_assets() -> None:
    client = TestClient(app)
    css_res = client.get("/static/css/studio.css")
    assert css_res.status_code == 200
    assert "--primary:" in css_res.text

    js_res = client.get("/static/js/app.js")
    assert js_res.status_code == 200
    assert "initGraphCanvas" in js_res.text
