"""Database schema analyzer — parses CREATE TABLE statements and flags issues.

Detects indexing opportunities, normalization problems, and common
anti-patterns in database schema definitions without requiring a live
database connection or AI calls.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class TableColumn:
    """Parsed column from a CREATE TABLE statement."""

    name: str
    data_type: str
    nullable: bool
    is_primary_key: bool
    is_unique: bool
    has_default: bool
    raw_definition: str


@dataclass
class TableDefinition:
    """Parsed CREATE TABLE with columns, constraints, and indexes."""

    name: str
    columns: list[TableColumn]
    primary_key: list[str]
    foreign_keys: list[dict]
    unique_constraints: list[list[str]]
    indexes: list[str]
    raw_sql: str


@dataclass
class SchemaIssue:
    """A single issue found during schema analysis."""

    table: str
    severity: str  # "warning" | "info" | "error"
    category: str  # "indexing" | "normalization" | "anti-pattern"
    message: str
    suggestion: str


def parse_create_tables(schema_sql: str) -> list[TableDefinition]:
    """Extract and parse all CREATE TABLE statements from raw SQL.

    Args:
        schema_sql: Raw SQL containing one or more CREATE TABLE statements.

    Returns:
        List of parsed table definitions.
    """
    tables: list[TableDefinition] = []

    # Find CREATE TABLE ... ( and then match balanced parentheses
    header_pattern = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
        r"(?:`?[\w.]+`?\.)?`?([\w]+)`?\s*\(",
        re.IGNORECASE,
    )

    for match in header_pattern.finditer(schema_sql):
        table_name = match.group(1)
        # Find the matching closing paren by tracking depth
        start = match.end()  # position right after the opening (
        body = _extract_balanced_parens(schema_sql, start)
        if body is None:
            continue

        raw_sql = schema_sql[match.start() : start + len(body) + 1]  # include closing )

        columns, pk, fks, uniques, indexes = _parse_table_body(body)

        tables.append(
            TableDefinition(
                name=table_name,
                columns=columns,
                primary_key=pk,
                foreign_keys=fks,
                unique_constraints=uniques,
                indexes=indexes,
                raw_sql=raw_sql,
            )
        )

    return tables


def _extract_balanced_parens(text: str, start: int) -> Optional[str]:
    """Extract content up to the matching closing parenthesis.

    Args:
        text: Full SQL string.
        start: Position right after the opening '('.

    Returns:
        The content between the balanced parens, or None if unbalanced.
    """
    depth = 1
    pos = start
    while pos < len(text) and depth > 0:
        if text[pos] == '(':
            depth += 1
        elif text[pos] == ')':
            depth -= 1
        pos += 1
    if depth != 0:
        return None
    return text[start : pos - 1]  # exclude the closing )


def _parse_table_body(
    body: str,
) -> tuple[list[TableColumn], list[str], list[dict], list[list[str]], list[str]]:
    """Parse the inner body of a CREATE TABLE statement."""
    columns: list[TableColumn] = []
    primary_key: list[str] = []
    foreign_keys: list[dict] = []
    unique_constraints: list[list[str]] = []
    indexes: list[str] = []

    # Split on commas, but respect parentheses depth
    parts = _split_respecting_parens(body)

    for part in parts:
        stripped = part.strip()
        upper = stripped.upper()

        # Table-level PRIMARY KEY
        if upper.startswith("PRIMARY KEY"):
            pk_match = re.search(r"\((.+?)\)", stripped)
            if pk_match:
                primary_key = [c.strip().strip("`\"'") for c in pk_match.group(1).split(",")]
            continue

        # FOREIGN KEY
        if upper.startswith("FOREIGN KEY"):
            fk_match = re.search(
                r"FOREIGN\s+KEY\s*\((.+?)\)\s*REFERENCES\s+(\w+)\s*\((.+?)\)",
                stripped,
                re.IGNORECASE,
            )
            if fk_match:
                foreign_keys.append({
                    "columns": [c.strip().strip("`\"'") for c in fk_match.group(1).split(",")],
                    "ref_table": fk_match.group(2),
                    "ref_columns": [c.strip().strip("`\"'") for c in fk_match.group(3).split(",")],
                })
            continue

        # UNIQUE constraint
        if upper.startswith("UNIQUE"):
            uq_match = re.search(r"\((.+?)\)", stripped)
            if uq_match:
                unique_constraints.append(
                    [c.strip().strip("`\"'") for c in uq_match.group(1).split(",")]
                )
            continue

        # INDEX / KEY
        if upper.startswith(("INDEX", "KEY")):
            idx_match = re.search(r"\((.+?)\)", stripped)
            if idx_match:
                indexes.append(idx_match.group(1))
            continue

        # CONSTRAINT ... (skip other constraints)
        if upper.startswith("CONSTRAINT"):
            # Could be a named PK, FK, or UNIQUE
            if "PRIMARY KEY" in upper:
                pk_match = re.search(r"PRIMARY\s+KEY\s*\((.+?)\)", stripped, re.IGNORECASE)
                if pk_match:
                    primary_key = [c.strip().strip("`\"'") for c in pk_match.group(1).split(",")]
            elif "FOREIGN KEY" in upper:
                fk_match = re.search(
                    r"FOREIGN\s+KEY\s*\((.+?)\)\s*REFERENCES\s+(\w+)\s*\((.+?)\)",
                    stripped,
                    re.IGNORECASE,
                )
                if fk_match:
                    foreign_keys.append({
                        "columns": [c.strip().strip("`\"'") for c in fk_match.group(1).split(",")],
                        "ref_table": fk_match.group(2),
                        "ref_columns": [c.strip().strip("`\"'") for c in fk_match.group(3).split(",")],
                    })
            elif "UNIQUE" in upper:
                uq_match = re.search(r"UNIQUE\s*\((.+?)\)", stripped, re.IGNORECASE)
                if uq_match:
                    unique_constraints.append(
                        [c.strip().strip("`\"'") for c in uq_match.group(1).split(",")]
                    )
            continue

        # Regular column definition
        col = _parse_column(stripped, primary_key)
        if col:
            columns.append(col)

    return columns, primary_key, foreign_keys, unique_constraints, indexes


def _parse_column(definition: str, existing_pk: list[str]) -> Optional[TableColumn]:
    """Parse a single column definition."""
    # Match: column_name data_type (possibly with parens like VARCHAR(100)) [constraints...]
    col_match = re.match(
        r"`?([\w]+)`?\s+(\w+(?:\s*\([^)]*\))?)\s*(.*)",
        definition.strip(),
        re.IGNORECASE | re.DOTALL,
    )
    if not col_match:
        return None

    name = col_match.group(1)
    data_type = col_match.group(2).upper()
    constraints = col_match.group(3).upper()

    is_pk = "PRIMARY KEY" in constraints
    if is_pk and name not in existing_pk:
        existing_pk.append(name)

    return TableColumn(
        name=name,
        data_type=data_type,
        nullable="NOT NULL" not in constraints and not is_pk,
        is_primary_key=is_pk,
        is_unique="UNIQUE" in constraints,
        has_default="DEFAULT" in constraints,
        raw_definition=definition.strip(),
    )


def _split_respecting_parens(text: str) -> list[str]:
    """Split by comma, but ignore commas inside parentheses."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []

    for char in text:
        if char == "(":
            depth += 1
            current.append(char)
        elif char == ")":
            depth -= 1
            current.append(char)
        elif char == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)

    if current:
        parts.append("".join(current))

    return parts


def analyze_schema(tables: list[TableDefinition]) -> list[SchemaIssue]:
    """Run all analysis checks across parsed tables.

    Args:
        tables: Parsed table definitions from parse_create_tables().

    Returns:
        List of issues found, sorted by severity.
    """
    issues: list[SchemaIssue] = []

    for table in tables:
        issues.extend(_check_missing_primary_key(table))
        issues.extend(_check_indexing_opportunities(table))
        issues.extend(_check_normalization(table))
        issues.extend(_check_anti_patterns(table))
        issues.extend(_check_foreign_key_indexes(table))
        issues.extend(_check_nullable_booleans(table))

    # Sort: error > warning > info
    severity_order = {"error": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda i: severity_order.get(i.severity, 99))

    return issues


def _check_missing_primary_key(table: TableDefinition) -> list[SchemaIssue]:
    """Tables should have a primary key."""
    if not table.primary_key and not any(c.is_primary_key for c in table.columns):
        return [
            SchemaIssue(
                table=table.name,
                severity="error",
                category="anti-pattern",
                message="Table has no primary key defined.",
                suggestion="Add a primary key column (e.g., `id SERIAL PRIMARY KEY` for PostgreSQL).",
            )
        ]
    return []


def _check_indexing_opportunities(table: TableDefinition) -> list[SchemaIssue]:
    """Suggest indexes on foreign key columns and commonly filtered columns."""
    issues: list[SchemaIssue] = []

    fk_columns = set()
    for fk in table.foreign_keys:
        fk_columns.update(fk["columns"])

    indexed_columns = set()
    for idx in table.indexes:
        indexed_columns.update(c.strip().strip("`\"'") for c in idx.split(","))

    # Also treat PK and unique columns as indexed
    indexed_columns.update(table.primary_key)
    for uq in table.unique_constraints:
        indexed_columns.update(uq)
    for col in table.columns:
        if col.is_primary_key or col.is_unique:
            indexed_columns.add(col.name)

    for fk_col in fk_columns:
        if fk_col not in indexed_columns:
            issues.append(
                SchemaIssue(
                    table=table.name,
                    severity="warning",
                    category="indexing",
                    message=f"Foreign key column `{fk_col}` has no index.",
                    suggestion=f"CREATE INDEX idx_{table.name}_{fk_col} ON {table.name}({fk_col});",
                )
            )

    # Columns ending in _id, _at, _date are commonly queried — suggest indexes
    for col in table.columns:
        if col.name in indexed_columns or col.name in fk_columns:
            continue
        if col.name.endswith(("_id", "_at", "_date")) and col.name not in indexed_columns:
            issues.append(
                SchemaIssue(
                    table=table.name,
                    severity="info",
                    category="indexing",
                    message=f"Column `{col.name}` looks like a commonly queried field but has no index.",
                    suggestion=f"CREATE INDEX idx_{table.name}_{col.name} ON {table.name}({col.name});",
                )
            )

    return issues


def _check_normalization(table: TableDefinition) -> list[SchemaIssue]:
    """Flag potential normalization issues."""
    issues: list[SchemaIssue] = []

    # Too many columns might indicate a need to split the table
    if len(table.columns) > 20:
        issues.append(
            SchemaIssue(
                table=table.name,
                severity="warning",
                category="normalization",
                message=f"Table has {len(table.columns)} columns — consider splitting into related tables.",
                suggestion="Group related columns into separate tables linked by foreign keys.",
            )
        )

    # Repeated column name patterns (e.g., phone1, phone2, phone3)
    base_names: dict[str, int] = {}
    for col in table.columns:
        # Strip trailing digits
        base = re.sub(r"\d+$", "", col.name)
        base_names[base] = base_names.get(base, 0) + 1

    for base, count in base_names.items():
        if count >= 3 and base:
            issues.append(
                SchemaIssue(
                    table=table.name,
                    severity="warning",
                    category="normalization",
                    message=f"Repeated column pattern detected: `{base}*` ({count} occurrences).",
                    suggestion=f"Consider normalizing into a separate `{base}s` table with a foreign key back to `{table.name}`.",
                )
            )

    return issues


def _check_anti_patterns(table: TableDefinition) -> list[SchemaIssue]:
    """Detect common schema anti-patterns."""
    issues: list[SchemaIssue] = []

    for col in table.columns:
        dtype = col.data_type.upper()

        # TEXT/BLOB for status fields — should be ENUM or small VARCHAR
        if dtype in ("TEXT", "LONGTEXT", "CLOB") and any(
            keyword in col.name.lower()
            for keyword in ("status", "type", "category", "role", "state")
        ):
            issues.append(
                SchemaIssue(
                    table=table.name,
                    severity="warning",
                    category="anti-pattern",
                    message=f"Column `{col.name}` uses {dtype} for what looks like an enum field.",
                    suggestion=f"Use VARCHAR(50) or an ENUM type for `{col.name}` — TEXT is wasteful for constrained values.",
                )
            )

        # VARCHAR(255) as default — often a sign of no thought given to limits
        if "VARCHAR(255)" in dtype and col.name.lower() not in ("email", "url", "path"):
            issues.append(
                SchemaIssue(
                    table=table.name,
                    severity="info",
                    category="anti-pattern",
                    message=f"Column `{col.name}` uses VARCHAR(255) — the 'I didn't think about it' default.",
                    suggestion=f"Set an appropriate max length for `{col.name}` based on actual data requirements.",
                )
            )

        # FLOAT/DOUBLE for monetary values
        if dtype in ("FLOAT", "DOUBLE", "REAL") and any(
            keyword in col.name.lower()
            for keyword in ("price", "amount", "cost", "balance", "total", "salary")
        ):
            issues.append(
                SchemaIssue(
                    table=table.name,
                    severity="error",
                    category="anti-pattern",
                    message=f"Column `{col.name}` uses {dtype} for monetary values — floating point causes rounding errors.",
                    suggestion=f"Use DECIMAL(10,2) or NUMERIC(10,2) for `{col.name}` to avoid precision loss.",
                )
            )

    return issues


def _check_foreign_key_indexes(table: TableDefinition) -> list[SchemaIssue]:
    """Warn if foreign keys reference tables that might not have indexes."""
    issues: list[SchemaIssue] = []

    for fk in table.foreign_keys:
        if len(fk["columns"]) > 1:
            issues.append(
                SchemaIssue(
                    table=table.name,
                    severity="info",
                    category="indexing",
                    message=f"Composite foreign key ({', '.join(fk['columns'])}) → {fk['ref_table']} — ensure a matching composite index exists.",
                    suggestion=f"CREATE INDEX idx_{table.name}_{'_'.join(fk['columns'])} ON {table.name}({', '.join(fk['columns'])});",
                )
            )

    return issues


def _check_nullable_booleans(table: TableDefinition) -> list[SchemaIssue]:
    """Boolean columns should typically not be nullable (three-valued logic is confusing)."""
    issues: list[SchemaIssue] = []

    for col in table.columns:
        dtype = col.data_type.upper()
        if dtype in ("BOOLEAN", "BOOL", "TINYINT(1)") and col.nullable:
            issues.append(
                SchemaIssue(
                    table=table.name,
                    severity="warning",
                    category="anti-pattern",
                    message=f"Boolean column `{col.name}` is nullable — NULL introduces three-valued logic.",
                    suggestion=f"Add NOT NULL DEFAULT false (or DEFAULT 0) to `{col.name}`.",
                )
            )

    return issues


def generate_summary(tables: list[TableDefinition], issues: list[SchemaIssue]) -> str:
    """Generate a human-readable summary of the schema analysis.

    Args:
        tables: Parsed table definitions.
        issues: Issues found during analysis.

    Returns:
        Markdown-formatted summary string.
    """
    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")
    info_count = sum(1 for i in issues if i.severity == "info")

    total_cols = sum(len(t.columns) for t in tables)
    total_fks = sum(len(t.foreign_keys) for t in tables)

    summary_parts = [
        f"Analyzed {len(tables)} table(s) with {total_cols} total columns and {total_fks} foreign key(s).",
    ]

    if not issues:
        summary_parts.append("No issues detected — schema looks clean!")
    else:
        summary_parts.append(
            f"Found {len(issues)} issue(s): {error_count} error(s), "
            f"{warning_count} warning(s), {info_count} informational."
        )

    return " ".join(summary_parts)
