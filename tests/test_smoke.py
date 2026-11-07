"""Fast, offline smoke tests. The Stop hook runs these after every Claude turn. Keep them <10s."""

import pytest
from fastapi.testclient import TestClient

from api.app.main import app


@pytest.fixture(autouse=True)
def _mock_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")


client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_generate_mock():
    r = client.post("/api/generate", json={"prompt": "hello"})
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "mock"
    assert "hello" in body["text"]


def test_generate_validates_input():
    assert client.post("/api/generate", json={"prompt": ""}).status_code == 422


def test_unknown_provider_returns_502(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    assert client.post("/api/generate", json={"prompt": "x"}).status_code == 502


def test_frontend_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "<html" in r.text.lower()
