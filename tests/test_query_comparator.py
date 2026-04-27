"""Tests for query comparison engine — all offline, no AI needed."""

import pytest
from fastapi.testclient import TestClient

from main import app
from src.core.query_comparator import (
    count_tokens,
    extract_clauses,
    compute_structural_diff,
    compare_queries,
    estimate_improvement,
)


client = TestClient(app)


class TestCountTokens:
    def test_simple_query(self):
        count = count_tokens("SELECT id FROM users")
        assert count > 0

    def test_empty_query(self):
        count = count_tokens("")
        assert count == 0

    def test_complex_query_more_tokens(self):
        simple = count_tokens("SELECT id FROM users")
        complex_q = count_tokens(
            "SELECT u.id, u.name, o.total FROM users u "
            "JOIN orders o ON u.id = o.user_id WHERE o.total > 100"
        )
        assert complex_q > simple

    def test_whitespace_normalization(self):
        sparse = count_tokens("SELECT   id   FROM   users")
        normal = count_tokens("SELECT id FROM users")
        assert sparse == normal


class TestExtractClauses:
    def test_select_from_where(self):
        clauses = extract_clauses("SELECT id, name FROM users WHERE active = 1")
        assert "SELECT" in clauses
        assert "FROM" in clauses
        assert "WHERE" in clauses

    def test_missing_clauses(self):
        clauses = extract_clauses("SELECT 1")
        assert "WHERE" not in clauses

    def test_join_clause(self):
        clauses = extract_clauses(
            "SELECT u.id FROM users u JOIN orders o ON u.id = o.user_id"
        )
        assert "JOIN" in clauses or "INNER JOIN" in clauses


class TestComputeStructuralDiff:
    def test_added_clause(self):
        diff = compute_structural_diff(
            "SELECT * FROM users",
            "SELECT * FROM users WHERE active = 1",
        )
        assert len(diff["added"]) >= 1

    def test_removed_clause(self):
        diff = compute_structural_diff(
            "SELECT * FROM users WHERE active = 1 ORDER BY name",
            "SELECT * FROM users WHERE active = 1",
        )
        assert len(diff["removed"]) >= 1

    def test_modified_clause(self):
        diff = compute_structural_diff(
            "SELECT * FROM users WHERE active = 1",
            "SELECT id, name FROM users WHERE active = 1",
        )
        assert len(diff["modified"]) >= 1

    def test_identical_queries(self):
        diff = compute_structural_diff(
            "SELECT id FROM users",
            "SELECT id FROM users",
        )
        assert diff["added"] == []
        assert diff["removed"] == []
        assert diff["modified"] == []


class TestEstimateImprovement:
    def test_issues_resolved(self):
        result = estimate_improvement(
            original_issues=["SELECT * is bad", "Missing WHERE"],
            optimized_issues=["Missing WHERE"],
            token_reduction_pct=5.0,
        )
        assert "1 issue(s) resolved" in result

    def test_significant_simplification(self):
        result = estimate_improvement(
            original_issues=[],
            optimized_issues=[],
            token_reduction_pct=30.0,
        )
        assert "significant" in result.lower()

    def test_no_change(self):
        result = estimate_improvement(
            original_issues=[],
            optimized_issues=[],
            token_reduction_pct=0.0,
        )
        assert "minimal" in result.lower()


class TestCompareQueries:
    def test_basic_comparison(self):
        result = compare_queries(
            "SELECT * FROM users WHERE UPPER(name) = 'JOHN' ORDER BY created_at",
            "SELECT id, name FROM users WHERE name = 'JOHN' ORDER BY created_at LIMIT 100",
        )
        assert result["original_token_count"] > 0
        assert result["optimized_token_count"] > 0
        assert "original_formatted" in result
        assert "optimized_formatted" in result
        assert "issues_resolved" in result
        assert "structural_changes" in result

    def test_issue_resolution_detection(self):
        result = compare_queries(
            "SELECT * FROM users",
            "SELECT id, name FROM users",
        )
        assert len(result["issues_resolved"]) >= 1  # SELECT * resolved

    def test_new_issue_detection(self):
        result = compare_queries(
            "SELECT id FROM users WHERE id = 1",
            "SELECT * FROM users WHERE id = 1",
        )
        assert len(result["new_issues"]) >= 1

    def test_token_reduction_calculated(self):
        result = compare_queries(
            "SELECT u.id, u.name, u.email, u.phone, u.address FROM users u "
            "WHERE u.active = 1 AND u.role = 'admin' ORDER BY u.name",
            "SELECT id, name FROM users WHERE active = 1 LIMIT 50",
        )
        assert result["token_reduction_pct"] > 0


class TestCompareEndpoint:
    def test_compare_returns_200(self):
        response = client.post(
            "/api/v1/compare",
            json={
                "original_query": "SELECT * FROM users ORDER BY name",
                "optimized_query": "SELECT id, name FROM users ORDER BY name LIMIT 100",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "original_formatted" in data
        assert "optimized_formatted" in data
        assert "token_reduction_pct" in data
        assert "structural_changes" in data

    def test_compare_rejects_empty(self):
        response = client.post(
            "/api/v1/compare",
            json={"original_query": "", "optimized_query": "SELECT 1"},
        )
        assert response.status_code == 422

    def test_compare_structural_changes_format(self):
        response = client.post(
            "/api/v1/compare",
            json={
                "original_query": "SELECT * FROM users",
                "optimized_query": "SELECT id FROM users WHERE active = 1",
            },
        )
        data = response.json()
        sc = data["structural_changes"]
        assert "added" in sc
        assert "removed" in sc
        assert "modified" in sc
