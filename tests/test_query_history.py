"""Tests for query history store and analytics endpoints."""

import pytest
from fastapi.testclient import TestClient

from main import app
from src.services.query_history import QueryHistoryStore


client = TestClient(app)


class TestQueryHistoryStore:
    """Unit tests for the in-memory history store."""

    def setup_method(self):
        """Fresh store for each test."""
        self.store = QueryHistoryStore()

    def test_log_query_creates_record(self):
        record = self.store.log_query(
            sql_query="SELECT * FROM users",
            database_type="postgresql",
            issues=["SELECT * detected"],
            optimization_score=70.0,
            endpoint="analyze",
        )
        assert record.id is not None
        assert record.sql_query == "SELECT * FROM users"
        assert record.optimization_score == 70.0

    def test_log_query_clamps_score(self):
        record = self.store.log_query(
            sql_query="SELECT 1",
            database_type="generic",
            issues=[],
            optimization_score=150.0,
            endpoint="analyze",
        )
        assert record.optimization_score == 100.0

        record2 = self.store.log_query(
            sql_query="SELECT 1",
            database_type="generic",
            issues=[],
            optimization_score=-20.0,
            endpoint="analyze",
        )
        assert record2.optimization_score == 0.0

    def test_get_history_returns_most_recent_first(self):
        self.store.log_query("SELECT 1", "generic", [], 100.0, "analyze")
        self.store.log_query("SELECT 2", "generic", [], 80.0, "analyze")
        self.store.log_query("SELECT 3", "generic", [], 60.0, "analyze")

        records = self.store.get_history(limit=10)
        assert len(records) == 3
        assert records[0].sql_query == "SELECT 3"
        assert records[2].sql_query == "SELECT 1"

    def test_get_history_with_pagination(self):
        for i in range(10):
            self.store.log_query(f"SELECT {i}", "generic", [], 90.0, "analyze")

        page1 = self.store.get_history(limit=3, offset=0)
        page2 = self.store.get_history(limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 3
        assert page1[0].sql_query != page2[0].sql_query

    def test_get_history_filter_by_database_type(self):
        self.store.log_query("SELECT 1", "postgresql", [], 100.0, "analyze")
        self.store.log_query("SELECT 2", "mysql", [], 80.0, "analyze")
        self.store.log_query("SELECT 3", "postgresql", [], 90.0, "analyze")

        pg_records = self.store.get_history(database_type="postgresql")
        assert len(pg_records) == 2
        assert all(r.database_type == "postgresql" for r in pg_records)

    def test_get_stats_empty_store(self):
        stats = self.store.get_stats()
        assert stats["total_queries"] == 0
        assert stats["avg_optimization_score"] == 0.0
        assert stats["most_common_issues"] == []

    def test_get_stats_with_data(self):
        self.store.log_query(
            "SELECT * FROM a", "postgresql",
            ["SELECT * detected", "Missing WHERE"],
            55.0, "analyze",
        )
        self.store.log_query(
            "SELECT * FROM b", "mysql",
            ["SELECT * detected"],
            85.0, "analyze",
        )
        self.store.log_query(
            "SELECT id FROM c", "postgresql",
            [],
            100.0, "chat",
        )

        stats = self.store.get_stats()
        assert stats["total_queries"] == 3
        assert stats["avg_optimization_score"] == 80.0
        assert stats["most_common_issues"][0]["issue"] == "SELECT * detected"
        assert stats["most_common_issues"][0]["count"] == 2
        assert stats["queries_by_database"]["postgresql"] == 2
        assert stats["queries_by_endpoint"]["analyze"] == 2

    def test_eviction_at_max_capacity(self):
        store = QueryHistoryStore(max_records=5)
        for i in range(10):
            store.log_query(f"SELECT {i}", "generic", [], 90.0, "analyze")
        assert len(store._records) == 5
        # Oldest records evicted — most recent kept
        assert store._records[0].sql_query == "SELECT 5"

    def test_get_record_by_id(self):
        record = self.store.log_query("SELECT 1", "generic", [], 100.0, "analyze")
        found = self.store.get_record_by_id(record.id)
        assert found is not None
        assert found.sql_query == "SELECT 1"

    def test_get_record_by_id_not_found(self):
        assert self.store.get_record_by_id("nonexistent") is None

    def test_clear(self):
        self.store.log_query("SELECT 1", "generic", [], 100.0, "analyze")
        self.store.log_query("SELECT 2", "generic", [], 90.0, "analyze")
        removed = self.store.clear()
        assert removed == 2
        assert len(self.store._records) == 0


class TestQueryHistoryEndpoints:
    """Integration tests for the history API endpoints."""

    def test_get_history_returns_200(self):
        response = client.get("/api/v1/history")
        assert response.status_code == 200
        data = response.json()
        assert "records" in data
        assert "total" in data

    def test_get_stats_returns_200(self):
        response = client.get("/api/v1/history/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_queries" in data
        assert "avg_optimization_score" in data
        assert "most_common_issues" in data

    def test_history_pagination_params(self):
        response = client.get("/api/v1/history?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0

    def test_history_invalid_limit(self):
        response = client.get("/api/v1/history?limit=0")
        assert response.status_code == 422
