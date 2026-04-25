"""Tests for static SQL analysis — no AI/API keys needed."""

import pytest
from src.core.sql_analyzer import format_sql, detect_issues, suggest_indexes, extract_tables


class TestFormatSQL:
    def test_basic_formatting(self):
        sql = "select id, name from users where active = 1"
        result = format_sql(sql)
        assert "SELECT" in result
        assert "FROM" in result
        assert "WHERE" in result

    def test_complex_query_formatting(self):
        sql = "select u.id, u.name, o.total from users u join orders o on u.id = o.user_id where o.total > 100 order by o.total desc"
        result = format_sql(sql)
        assert "JOIN" in result
        assert "ORDER BY" in result


class TestDetectIssues:
    def test_select_star(self):
        issues = detect_issues("SELECT * FROM users")
        assert any("SELECT *" in i for i in issues)

    def test_delete_without_where(self):
        issues = detect_issues("DELETE FROM users")
        assert any("WHERE" in i for i in issues)

    def test_update_without_where(self):
        issues = detect_issues("UPDATE users SET active = 0")
        assert any("WHERE" in i for i in issues)

    def test_leading_wildcard_like(self):
        issues = detect_issues("SELECT id FROM users WHERE name LIKE '%john'")
        assert any("wildcard" in i.lower() for i in issues)

    def test_order_by_without_limit(self):
        issues = detect_issues("SELECT id FROM users ORDER BY created_at")
        assert any("LIMIT" in i for i in issues)

    def test_distinct_with_join(self):
        issues = detect_issues("SELECT DISTINCT u.id FROM users u JOIN orders o ON u.id = o.user_id")
        assert any("DISTINCT" in i for i in issues)

    def test_function_in_where(self):
        issues = detect_issues("SELECT id FROM users WHERE UPPER(name) = 'JOHN'")
        assert any("Function" in i or "function" in i for i in issues)

    def test_clean_query_no_issues(self):
        issues = detect_issues("SELECT id, name FROM users WHERE id = 1")
        assert len(issues) == 0


class TestExtractTables:
    def test_single_table(self):
        tables = extract_tables("SELECT id FROM users WHERE active = 1")
        assert "users" in tables

    def test_join_tables(self):
        tables = extract_tables("SELECT u.id FROM users u JOIN orders o ON u.id = o.user_id")
        assert len(tables) >= 1


class TestSuggestIndexes:
    def test_where_clause_suggestion(self):
        suggestions = suggest_indexes("SELECT id FROM users WHERE email = 'test@test.com'")
        assert any("WHERE" in s for s in suggestions)

    def test_join_index_suggestion(self):
        suggestions = suggest_indexes("SELECT u.id FROM users u JOIN orders o ON u.id = o.user_id")
        assert any("JOIN" in s or "join" in s for s in suggestions)

    def test_order_by_suggestion(self):
        suggestions = suggest_indexes("SELECT id FROM users WHERE active = 1 ORDER BY created_at")
        assert any("ORDER BY" in s for s in suggestions)
