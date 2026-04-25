"""API routes — thin layer that validates input and delegates to services."""

import logging
from fastapi import APIRouter, HTTPException

from src.models.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    SQLAnalysisRequest,
    SQLAnalysisResponse,
)
from src.services import ai_service

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
        return SQLAnalysisResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
