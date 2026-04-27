"""Request/response schemas for the API layer."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime


class DatabaseType(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLSERVER = "sqlserver"
    ORACLE = "oracle"
    GENERIC = "generic"


class ChatRequest(BaseModel):
    """Incoming user message with optional database context."""
    message: str = Field(..., min_length=1, max_length=10000)
    database_type: DatabaseType = DatabaseType.GENERIC
    # Optional SQL for analysis
    sql_query: Optional[str] = Field(None, max_length=50000)
    # Optional execution plan output for explanation
    execution_plan: Optional[str] = Field(None, max_length=50000)
    # Conversation history for multi-turn context
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Structured response from the assistant."""
    reply: str
    suggested_sql: Optional[str] = None
    optimization_tips: Optional[list[str]] = None
    session_id: str


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"


class SQLAnalysisRequest(BaseModel):
    """Dedicated endpoint for deep SQL analysis."""
    sql_query: str = Field(..., min_length=1, max_length=50000)
    database_type: DatabaseType = DatabaseType.GENERIC
    include_optimization: bool = True
    include_explanation: bool = True


class SQLAnalysisResponse(BaseModel):
    original_sql: str
    formatted_sql: str
    explanation: str
    issues: list[str]
    optimized_sql: Optional[str] = None
    optimization_notes: list[str]
    index_suggestions: list[str]


# ── Query History & Analytics ────────────────────────────────────────────────


class QueryHistoryRecord(BaseModel):
    """Single entry in the query analysis history."""

    id: str
    sql_query: str
    database_type: str
    issues: list[str]
    optimization_score: float
    timestamp: float
    endpoint: str


class QueryHistoryResponse(BaseModel):
    """Paginated list of historical query records."""

    records: list[QueryHistoryRecord]
    total: int
    limit: int
    offset: int


class QueryStatsResponse(BaseModel):
    """Aggregate analytics across all recorded queries."""

    total_queries: int
    avg_optimization_score: float
    most_common_issues: list[dict]
    queries_by_database: dict[str, int]
    queries_by_endpoint: dict[str, int]
    score_distribution: dict[str, int]


# ── Schema Analyzer ──────────────────────────────────────────────────────────


class SchemaAnalysisRequest(BaseModel):
    """Request body for database schema analysis."""

    schema_sql: str = Field(
        ...,
        min_length=1,
        max_length=100000,
        description="One or more CREATE TABLE statements to analyze.",
    )
    database_type: DatabaseType = DatabaseType.GENERIC


class SchemaIssue(BaseModel):
    """A single issue found during schema analysis."""

    table: str
    severity: str  # "warning" | "info" | "error"
    category: str  # "indexing" | "normalization" | "anti-pattern"
    message: str
    suggestion: str


class SchemaAnalysisResponse(BaseModel):
    """Results from analyzing a database schema."""

    tables_analyzed: int
    issues: list[SchemaIssue]
    summary: str


# ── Query Comparison ─────────────────────────────────────────────────────────


class QueryComparisonRequest(BaseModel):
    """Request body for comparing two SQL queries."""

    original_query: str = Field(..., min_length=1, max_length=50000)
    optimized_query: str = Field(..., min_length=1, max_length=50000)
    database_type: DatabaseType = DatabaseType.GENERIC


class QueryDiff(BaseModel):
    """Structural differences between two queries."""

    added: list[str]
    removed: list[str]
    modified: list[str]


class QueryComparisonResponse(BaseModel):
    """Side-by-side comparison of original vs. optimized query."""

    original_formatted: str
    optimized_formatted: str
    original_token_count: int
    optimized_token_count: int
    token_reduction_pct: float
    original_issues: list[str]
    optimized_issues: list[str]
    issues_resolved: list[str]
    issues_remaining: list[str]
    new_issues: list[str]
    structural_changes: QueryDiff
    estimated_improvement: str
