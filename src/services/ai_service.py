"""AI service — wraps the LLM provider with retry logic and session management."""

import logging
import uuid
from typing import Optional
from openai import AsyncOpenAI

from config import settings
from src.core.prompts import SYSTEM_PROMPT, SQL_ANALYSIS_PROMPT, EXECUTION_PLAN_PROMPT
from src.core.sql_analyzer import format_sql, detect_issues, suggest_indexes

logger = logging.getLogger(__name__)

# Simple in-memory session store — swap for Redis/DB in production
_sessions: dict[str, list[dict]] = {}


def _get_client() -> AsyncOpenAI:
    """Lazy client init so missing keys don't crash on import."""
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY not set — check your .env file")
    return AsyncOpenAI(api_key=settings.openai_api_key)


def _get_or_create_session(session_id: Optional[str]) -> tuple[str, list[dict]]:
    """Multi-turn context via session tracking."""
    sid = session_id or str(uuid.uuid4())
    if sid not in _sessions:
        _sessions[sid] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return sid, _sessions[sid]


async def chat(
    message: str,
    database_type: str = "generic",
    sql_query: Optional[str] = None,
    execution_plan: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict:
    """Main chat endpoint — handles natural language questions about SQL/databases."""
    client = _get_client()
    sid, history = _get_or_create_session(session_id)

    # Build context-aware user message
    user_content = f"[Database: {database_type}]\n\n{message}"
    if sql_query:
        user_content += f"\n\nSQL Query:\n```sql\n{sql_query}\n```"
    if execution_plan:
        user_content += f"\n\nExecution Plan:\n```\n{execution_plan}\n```"

    history.append({"role": "user", "content": user_content})

    # Keep conversation history bounded to avoid token blowup
    if len(history) > 20:
        history[:] = [history[0]] + history[-18:]

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=history,
            temperature=0.3,  # Low temp for accurate technical responses
            max_tokens=2000,
        )
        reply = response.choices[0].message.content
        history.append({"role": "assistant", "content": reply})

        # Extract any SQL suggestions from the response
        suggested_sql = _extract_sql_block(reply)
        tips = _extract_tips(reply)

        return {
            "reply": reply,
            "suggested_sql": suggested_sql,
            "optimization_tips": tips if tips else None,
            "session_id": sid,
        }
    except Exception as e:
        logger.error(f"AI service error: {e}")
        raise


async def analyze_sql(
    sql_query: str,
    database_type: str = "generic",
    include_optimization: bool = True,
    include_explanation: bool = True,
) -> dict:
    """Deep SQL analysis — combines static analysis with AI insight."""
    client = _get_client()

    # Static analysis first (free, instant)
    formatted = format_sql(sql_query)
    issues = detect_issues(sql_query)
    indexes = suggest_indexes(sql_query, database_type)

    # AI-powered deep analysis
    prompt = SQL_ANALYSIS_PROMPT.format(
        db_type=database_type,
        sql_query=sql_query,
        static_issues="\n".join(f"- {i}" for i in issues) if issues else "None detected",
        index_suggestions="\n".join(f"- {s}" for s in indexes) if indexes else "None",
    )

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=3000,
        )
        ai_analysis = response.choices[0].message.content
        optimized = _extract_sql_block(ai_analysis)

        return {
            "original_sql": sql_query,
            "formatted_sql": formatted,
            "explanation": ai_analysis,
            "issues": issues,
            "optimized_sql": optimized,
            "optimization_notes": _extract_tips(ai_analysis),
            "index_suggestions": indexes,
        }
    except Exception as e:
        logger.error(f"SQL analysis error: {e}")
        # Graceful degradation — return static analysis if AI fails
        return {
            "original_sql": sql_query,
            "formatted_sql": formatted,
            "explanation": "AI analysis unavailable — showing static analysis only.",
            "issues": issues,
            "optimized_sql": None,
            "optimization_notes": [],
            "index_suggestions": indexes,
        }


def _extract_sql_block(text: str) -> Optional[str]:
    """Pull the first SQL code block from AI response."""
    if "```sql" in text:
        start = text.index("```sql") + 6
        end = text.index("```", start)
        return text[start:end].strip()
    return None


def _extract_tips(text: str) -> list[str]:
    """Pull bullet-pointed tips from AI response."""
    tips = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith(("- ", "• ", "* ")) and len(stripped) > 10:
            tips.append(stripped.lstrip("-•* ").strip())
    return tips[:10]  # Cap at 10 tips
