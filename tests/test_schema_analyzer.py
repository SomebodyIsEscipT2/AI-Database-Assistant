"""Tests for database schema analyzer — all offline, no AI needed."""

import pytest
from fastapi.testclient import TestClient

from main import app
from src.core.schema_analyzer import (
    parse_create_tables,
    analyze_schema,
    generate_summary,
)


client = TestClient(app)


class TestParseCreateTables:
    """Unit tests for SQL DDL parsing."""

    def test_parse_single_table(self):
        sql = """
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(255) UNIQUE
        );
        """
        tables = parse_create_tables(sql)
        assert len(tables) == 1
        assert tables[0].name == "users"
        assert len(tables[0].columns) == 3

    def test_parse_multiple_tables(self):
        sql = """
        CREATE TABLE users (
            id INT PRIMARY KEY,
            name VARCHAR(100)
        );

        CREATE TABLE orders (
            id INT PRIMARY KEY,
            user_id INT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """
        tables = parse_create_tables(sql)
        assert len(tables) == 2
        assert tables[0].name == "users"
        assert tables[1].name == "orders"

    def test_parse_foreign_keys(self):
        sql = """
        CREATE TABLE orders (
            id INT PRIMARY KEY,
            user_id INT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """
        tables = parse_create_tables(sql)
        assert len(tables[0].foreign_keys) == 1
        assert tables[0].foreign_keys[0]["ref_table"] == "users"

    def test_parse_if_not_exists(self):
        sql = "CREATE TABLE IF NOT EXISTS products (id INT PRIMARY KEY, name VARCHAR(100));"
        tables = parse_create_tables(sql)
        assert len(tables) == 1
        assert tables[0].name == "products"

    def test_parse_empty_input(self):
        tables = parse_create_tables("SELECT * FROM users;")
        assert len(tables) == 0

    def test_parse_column_types(self):
        sql = """
        CREATE TABLE test (
            id INT PRIMARY KEY,
            price FLOAT,
            active BOOLEAN,
            bio TEXT
        );
        """
        tables = parse_create_tables(sql)
        columns = {c.name: c for c in tables[0].columns}
        assert "INT" in columns["id"].data_type
        assert "FLOAT" in columns["price"].data_type
        assert "BOOLEAN" in columns["active"].data_type


class TestAnalyzeSchema:
    """Tests for schema analysis checks."""

    def test_missing_primary_key(self):
        sql = "CREATE TABLE logs (message TEXT, created_at TIMESTAMP);"
        tables = parse_create_tables(sql)
        issues = analyze_schema(tables)
        assert any(
            "primary key" in i.message.lower() for i in issues
        )

    def test_float_for_money(self):
        sql = "CREATE TABLE products (id INT PRIMARY KEY, price FLOAT, amount DOUBLE);"
        tables = parse_create_tables(sql)
        issues = analyze_schema(tables)
        money_issues = [i for i in issues if "monetary" in i.message.lower() or "floating" in i.message.lower()]
        assert len(money_issues) >= 1

    def test_nullable_boolean(self):
        sql = "CREATE TABLE users (id INT PRIMARY KEY, active BOOLEAN);"
        tables = parse_create_tables(sql)
        issues = analyze_schema(tables)
        bool_issues = [i for i in issues if "boolean" in i.message.lower() or "nullable" in i.message.lower()]
        assert len(bool_issues) >= 1

    def test_text_for_status(self):
        sql = """
        CREATE TABLE orders (
            id INT PRIMARY KEY,
            status TEXT NOT NULL
        );
        """
        tables = parse_create_tables(sql)
        issues = analyze_schema(tables)
        assert any("enum" in i.suggestion.lower() or "varchar" in i.suggestion.lower() for i in issues)

    def test_unindexed_foreign_key(self):
        sql = """
        CREATE TABLE orders (
            id INT PRIMARY KEY,
            user_id INT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """
        tables = parse_create_tables(sql)
        issues = analyze_schema(tables)
        fk_issues = [i for i in issues if "foreign key" in i.message.lower() and "index" in i.message.lower()]
        assert len(fk_issues) >= 1

    def test_clean_schema_minimal_issues(self):
        sql = """
        CREATE TABLE users (
            id INT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(200) NOT NULL UNIQUE
        );
        """
        tables = parse_create_tables(sql)
        issues = analyze_schema(tables)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_varchar_255_anti_pattern(self):
        sql = """
        CREATE TABLE test (
            id INT PRIMARY KEY,
            description VARCHAR(255) NOT NULL
        );
        """
        tables = parse_create_tables(sql)
        issues = analyze_schema(tables)
        assert any("varchar(255)" in i.message.lower() for i in issues)

    def test_repeated_column_pattern(self):
        sql = """
        CREATE TABLE contacts (
            id INT PRIMARY KEY,
            phone1 VARCHAR(20),
            phone2 VARCHAR(20),
            phone3 VARCHAR(20)
        );
        """
        tables = parse_create_tables(sql)
        issues = analyze_schema(tables)
        assert any("repeated" in i.message.lower() for i in issues)

    def test_indexing_suggestion_for_date_columns(self):
        sql = """
        CREATE TABLE events (
            id INT PRIMARY KEY,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP
        );
        """
        tables = parse_create_tables(sql)
        issues = analyze_schema(tables)
        idx_issues = [i for i in issues if i.category == "indexing"]
        assert len(idx_issues) >= 1


class TestGenerateSummary:
    def test_summary_with_issues(self):
        sql = "CREATE TABLE logs (message TEXT, created_at TIMESTAMP);"
        tables = parse_create_tables(sql)
        issues = analyze_schema(tables)
        summary = generate_summary(tables, issues)
        assert "1 table" in summary
        assert "issue" in summary.lower()

    def test_summary_clean_schema(self):
        sql = "CREATE TABLE t (id INT PRIMARY KEY);"
        tables = parse_create_tables(sql)
        issues = analyze_schema(tables)
        summary = generate_summary(tables, issues)
        assert "1 table" in summary


class TestSchemaAnalyzerEndpoint:
    """Integration tests for the /schema/analyze endpoint."""

    def test_analyze_valid_schema(self):
        response = client.post(
            "/api/v1/schema/analyze",
            json={
                "schema_sql": "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));",
                "database_type": "postgresql",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tables_analyzed"] == 1
        assert "issues" in data
        assert "summary" in data

    def test_analyze_invalid_sql(self):
        response = client.post(
            "/api/v1/schema/analyze",
            json={"schema_sql": "SELECT * FROM users;"},
        )
        assert response.status_code == 400

    def test_analyze_empty_input(self):
        response = client.post(
            "/api/v1/schema/analyze",
            json={"schema_sql": ""},
        )
        assert response.status_code == 422

    def test_analyze_multiple_tables(self):
        schema = """
        CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));
        CREATE TABLE orders (id INT PRIMARY KEY, user_id INT, FOREIGN KEY (user_id) REFERENCES users(id));
        """
        response = client.post(
            "/api/v1/schema/analyze",
            json={"schema_sql": schema},
        )
        assert response.status_code == 200
        assert response.json()["tables_analyzed"] == 2
