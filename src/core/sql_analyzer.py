"""SQL parsing and static analysis — no AI needed for structural checks."""

import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where
from sqlparse.tokens import Keyword, DML
from typing import Optional


def format_sql(sql: str) -> str:
    """Pretty-print SQL for readability."""
    return sqlparse.format(
        sql,
        reindent=True,
        keyword_case="upper",
        indent_width=2,
    )


def extract_tables(sql: str) -> list[str]:
    """Pull table names from a query — useful for index suggestions."""
    parsed = sqlparse.parse(sql)
    tables = []
    for statement in parsed:
        _extract_tables_from_token(statement, tables)
    return list(set(tables))


def _extract_tables_from_token(token, tables: list[str]) -> None:
    """Recursive table extraction from parsed tokens."""
    if not hasattr(token, "tokens"):
        return

    from_seen = False
    for item in token.tokens:
        # Skip whitespace — it sits between FROM and the table name
        if item.is_whitespace:
            continue
        if item.ttype is Keyword and item.value.upper() in (
            "FROM", "JOIN", "INNER JOIN", "LEFT JOIN",
            "RIGHT JOIN", "FULL JOIN", "CROSS JOIN",
        ):
            from_seen = True
            continue
        if from_seen:
            if isinstance(item, Identifier):
                name = item.get_real_name()
                if name:
                    tables.append(name)
            elif isinstance(item, IdentifierList):
                for ident in item.get_identifiers():
                    if isinstance(ident, Identifier):
                        name = ident.get_real_name()
                        if name:
                            tables.append(name)
            from_seen = False
            continue
        # Recurse into sub-tokens (subqueries, etc.)
        _extract_tables_from_token(item, tables)


def detect_issues(sql: str) -> list[str]:
    """Flag common SQL anti-patterns without needing AI."""
    issues = []
    upper_sql = sql.upper().strip()

    # SELECT * is almost always a bad idea in production
    if "SELECT *" in upper_sql:
        issues.append("SELECT * pulls all columns — specify only what you need for better performance.")

    # Missing WHERE on UPDATE/DELETE is dangerous
    if ("UPDATE " in upper_sql or "DELETE " in upper_sql) and "WHERE" not in upper_sql:
        issues.append("⚠️ UPDATE/DELETE without WHERE clause — this affects ALL rows.")

    # Nested subqueries can often be CTEs
    if upper_sql.count("SELECT") > 2:
        issues.append("Multiple nested subqueries detected — consider using CTEs (WITH clause) for readability.")

    # LIKE with leading wildcard kills index usage
    if "LIKE '%" in upper_sql:
        issues.append("Leading wildcard in LIKE ('%...') prevents index usage — consider full-text search.")

    # ORDER BY without LIMIT on large result sets
    if "ORDER BY" in upper_sql and "LIMIT" not in upper_sql and "TOP " not in upper_sql and "FETCH" not in upper_sql:
        issues.append("ORDER BY without LIMIT/TOP — sorting large result sets is expensive without pagination.")

    # DISTINCT can mask join issues
    if "DISTINCT" in upper_sql and "JOIN" in upper_sql:
        issues.append("DISTINCT with JOIN often indicates a join producing duplicates — check join conditions.")

    # Functions in WHERE clause prevent index usage
    if "WHERE" in upper_sql:
        where_clause = upper_sql.split("WHERE", 1)[1]
        func_patterns = ["UPPER(", "LOWER(", "TRIM(", "CAST(", "CONVERT(", "YEAR(", "MONTH(", "DATEPART("]
        for func in func_patterns:
            if func in where_clause:
                issues.append(f"Function in WHERE clause ({func.rstrip('(')}) prevents index usage — use computed columns or adjust filter logic.")
                break

    return issues


def suggest_indexes(sql: str, db_type: str = "generic") -> list[str]:
    """Suggest indexes based on query structure."""
    suggestions = []
    upper_sql = sql.upper()
    tables = extract_tables(sql)

    # WHERE clause columns are prime index candidates
    if "WHERE" in upper_sql:
        suggestions.append(f"Add indexes on columns used in WHERE clause for tables: {', '.join(tables) if tables else 'detected tables'}")

    # JOIN columns need indexes
    if "JOIN" in upper_sql:
        suggestions.append("Ensure indexes exist on all JOIN key columns — missing join indexes are the #1 cause of slow queries.")

    # ORDER BY columns benefit from indexes
    if "ORDER BY" in upper_sql:
        suggestions.append("Consider composite indexes covering both WHERE and ORDER BY columns to avoid file sorts.")

    # GROUP BY columns
    if "GROUP BY" in upper_sql:
        suggestions.append("GROUP BY columns benefit from indexes — consider covering indexes that include the grouped and aggregated columns.")

    return suggestions
