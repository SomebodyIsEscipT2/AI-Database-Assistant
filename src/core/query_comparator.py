"""Query comparison engine — diff two SQL queries structurally.

Compares an original and optimized query to show token counts,
structural differences, resolved issues, and estimated improvements.
"""

import re
from typing import Optional

from src.core.sql_analyzer import format_sql, detect_issues


def count_tokens(sql: str) -> int:
    """Count meaningful tokens in a SQL query.

    Splits on whitespace and punctuation boundaries to approximate
    the number of logical tokens (keywords, identifiers, literals, operators).

    Args:
        sql: Raw SQL string.

    Returns:
        Token count.
    """
    # Normalize whitespace, then split on word boundaries and operators
    normalized = " ".join(sql.split())
    tokens = re.findall(r"[\w.]+|[^\s\w]", normalized)
    return len(tokens)


def extract_clauses(sql: str) -> dict[str, Optional[str]]:
    """Extract major SQL clauses from a query.

    Args:
        sql: Raw SQL string.

    Returns:
        Dict mapping clause names to their content, or None if absent.
    """
    upper = sql.upper()
    clauses: dict[str, Optional[str]] = {}

    clause_keywords = [
        "SELECT", "FROM", "WHERE", "JOIN", "INNER JOIN", "LEFT JOIN",
        "RIGHT JOIN", "FULL JOIN", "CROSS JOIN", "GROUP BY", "HAVING",
        "ORDER BY", "LIMIT", "OFFSET", "UNION", "WITH",
    ]

    # Find positions of each clause keyword
    positions: list[tuple[int, str]] = []
    for keyword in clause_keywords:
        idx = upper.find(keyword)
        if idx != -1:
            positions.append((idx, keyword))

    positions.sort(key=lambda x: x[0])

    for i, (pos, keyword) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(sql)
        content = sql[pos + len(keyword) : end].strip().rstrip(",;")
        clauses[keyword] = content if content else None

    return clauses


def compute_structural_diff(
    original: str, optimized: str
) -> dict[str, list[str]]:
    """Compare the structural clauses of two queries.

    Args:
        original: The original SQL query.
        optimized: The optimized SQL query.

    Returns:
        Dict with 'added', 'removed', and 'modified' clause lists.
    """
    orig_clauses = extract_clauses(original)
    opt_clauses = extract_clauses(optimized)

    all_keys = set(orig_clauses.keys()) | set(opt_clauses.keys())

    added: list[str] = []
    removed: list[str] = []
    modified: list[str] = []

    for key in sorted(all_keys):
        orig_val = orig_clauses.get(key)
        opt_val = opt_clauses.get(key)

        if orig_val is None and opt_val is not None:
            added.append(f"{key} clause added")
        elif orig_val is not None and opt_val is None:
            removed.append(f"{key} clause removed")
        elif orig_val != opt_val:
            modified.append(f"{key} clause modified")

    return {"added": added, "removed": removed, "modified": modified}


def estimate_improvement(
    original_issues: list[str],
    optimized_issues: list[str],
    token_reduction_pct: float,
) -> str:
    """Generate a human-readable improvement estimate.

    Args:
        original_issues: Issues in the original query.
        optimized_issues: Issues in the optimized query.
        token_reduction_pct: Percentage reduction in tokens.

    Returns:
        Human-readable improvement description.
    """
    resolved_count = len(original_issues) - len(
        [i for i in original_issues if i in optimized_issues]
    )

    parts: list[str] = []

    if resolved_count > 0:
        parts.append(f"{resolved_count} issue(s) resolved")

    if token_reduction_pct > 20:
        parts.append("significant query simplification")
    elif token_reduction_pct > 5:
        parts.append("moderate query simplification")
    elif token_reduction_pct < -10:
        parts.append("query expanded (may add clarity or features)")

    new_issues = [i for i in optimized_issues if i not in original_issues]
    if new_issues:
        parts.append(f"{len(new_issues)} new issue(s) introduced")

    if not parts:
        return "Minimal structural changes — review the optimized query for semantic improvements."

    return "; ".join(parts) + "."


def compare_queries(original: str, optimized: str) -> dict:
    """Full comparison of original vs optimized query.

    Args:
        original: The original SQL query.
        optimized: The optimized SQL query.

    Returns:
        Complete comparison result dict matching QueryComparisonResponse.
    """
    original_formatted = format_sql(original)
    optimized_formatted = format_sql(optimized)

    orig_tokens = count_tokens(original)
    opt_tokens = count_tokens(optimized)

    if orig_tokens > 0:
        token_reduction_pct = round(
            ((orig_tokens - opt_tokens) / orig_tokens) * 100, 2
        )
    else:
        token_reduction_pct = 0.0

    original_issues = detect_issues(original)
    optimized_issues = detect_issues(optimized)

    issues_resolved = [i for i in original_issues if i not in optimized_issues]
    issues_remaining = [i for i in original_issues if i in optimized_issues]
    new_issues = [i for i in optimized_issues if i not in original_issues]

    structural = compute_structural_diff(original, optimized)
    improvement = estimate_improvement(
        original_issues, optimized_issues, token_reduction_pct
    )

    return {
        "original_formatted": original_formatted,
        "optimized_formatted": optimized_formatted,
        "original_token_count": orig_tokens,
        "optimized_token_count": opt_tokens,
        "token_reduction_pct": token_reduction_pct,
        "original_issues": original_issues,
        "optimized_issues": optimized_issues,
        "issues_resolved": issues_resolved,
        "issues_remaining": issues_remaining,
        "new_issues": new_issues,
        "structural_changes": structural,
        "estimated_improvement": improvement,
    }
