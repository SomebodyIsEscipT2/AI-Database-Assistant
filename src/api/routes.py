"""API routes — thin layer that validates input and delegates to services."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.models.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    QueryHistoryRecord,
    QueryHistoryResponse,
    QueryStatsResponse,
    SQLAnalysisRequest,
    SQLAnalysisResponse,
)
from src.services import ai_service
from src.services.query_history import history_store
from src.core.sql_analyzer import detect_issues

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Liveness probe — always returns OK if the server is up."""
    return HealthResponse()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Conversational endpoint — ask anything about SQL/databases."""
    try:
        result = await ai_service.chat(
            message=request.message,
            database_type=request.database_type.value,
            sql_query=request.sql_query,
            execution_plan=request.execution_plan,
            session_id=request.session_id,
        )
        return ChatResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/analyze", response_model=SQLAnalysisResponse)
async def analyze_sql(request: SQLAnalysisRequest):
    """Deep SQL analysis — static checks + AI-powered optimization."""
    try:
        result = await ai_service.analyze_sql(
            sql_query=request.sql_query,
            database_type=request.database_type.value,
            include_optimization=request.include_optimization,
            include_explanation=request.include_explanation,
        )

        # Log to query history
        issues = result.get("issues", [])
        # Score: fewer issues = higher score, base 100 minus 15 per issue
        score = max(0.0, 100.0 - len(issues) * 15.0)
        history_store.log_query(
            sql_query=request.sql_query,
            database_type=request.database_type.value,
            issues=issues,
            optimization_score=score,
            endpoint="analyze",
        )

        return SQLAnalysisResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ── Query History & Analytics ─────────────────────────────────────────────────


@router.get("/history", response_model=QueryHistoryResponse)
async def get_query_history(
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    database_type: Optional[str] = Query(None, description="Filter by database type"),
):
    """Retrieve paginated query analysis history."""
    records = history_store.get_history(
        limit=limit, offset=offset, database_type=database_type
    )
    return QueryHistoryResponse(
        records=[QueryHistoryRecord(**r.__dict__) for r in records],
        total=len(history_store._records),
        limit=limit,
        offset=offset,
    )


@router.get("/history/stats", response_model=QueryStatsResponse)
async def get_query_stats():
    """Aggregate analytics across all analyzed queries."""
    return QueryStatsResponse(**history_store.get_stats())
