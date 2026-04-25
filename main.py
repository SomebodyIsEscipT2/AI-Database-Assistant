"""Entry point — boots the FastAPI server with structured logging."""

import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from src.api.routes import router

# Structured logging setup
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Database Assistant",
    description="AI-powered SQL optimization, query debugging, and database administration assistant. "
    "Supports PostgreSQL, MySQL, SQL Server, and Oracle.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — lock this down in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
async def startup():
    logger.info("AI Database Assistant starting up")
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set — AI features will be unavailable")
    logger.info(f"Server ready on {settings.host}:{settings.port}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level,
    )
