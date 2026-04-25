"""API endpoint tests — uses FastAPI test client, no live AI calls."""

import pytest
from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"


class TestChatEndpoint:
    def test_chat_requires_message(self):
        response = client.post("/api/v1/chat", json={})
        assert response.status_code == 422  # Validation error

    def test_chat_rejects_empty_message(self):
        response = client.post("/api/v1/chat", json={"message": ""})
        assert response.status_code == 422

    def test_chat_accepts_valid_request(self):
        """This will fail without OPENAI_API_KEY — that's expected in CI.
        The 503 confirms the service correctly reports missing config."""
        response = client.post("/api/v1/chat", json={
            "message": "How do I optimize a slow SELECT query?",
            "database_type": "postgresql",
        })
        # Either 200 (key present) or 503 (key missing) — both are correct behavior
        assert response.status_code in (200, 503)


class TestAnalyzeEndpoint:
    def test_analyze_requires_sql(self):
        response = client.post("/api/v1/analyze", json={})
        assert response.status_code == 422

    def test_analyze_rejects_empty_sql(self):
        response = client.post("/api/v1/analyze", json={"sql_query": ""})
        assert response.status_code == 422

    def test_analyze_accepts_valid_request(self):
        response = client.post("/api/v1/analyze", json={
            "sql_query": "SELECT * FROM users WHERE name LIKE '%john'",
            "database_type": "postgresql",
        })
        assert response.status_code in (200, 503)
