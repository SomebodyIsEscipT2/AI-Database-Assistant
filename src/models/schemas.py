"""Request/response schemas for the API layer."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


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
