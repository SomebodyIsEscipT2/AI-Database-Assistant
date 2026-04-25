# 🗄️ AI Database Assistant

> AI-powered SQL optimization, query debugging, and database administration assistant.  
> Built for multi-platform database environments — PostgreSQL, MySQL, SQL Server, Oracle.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-22%20passed-brightgreen.svg)]()

## What It Does

A conversational AI assistant that helps database professionals:

- **Write SQL** — Describe what you need in plain English, get optimized queries
- **Debug queries** — Paste broken SQL and get explanations + fixes
- **Optimize performance** — Static analysis + AI-powered suggestions for indexes, rewrites, and execution plan improvements
- **Explain execution plans** — Turn cryptic EXPLAIN output into plain English
- **Multi-database support** — PostgreSQL, MySQL, SQL Server, Oracle with dialect-aware suggestions

## Quick Start

```bash
# Clone
git clone https://github.com/escipionpedroza147-commits/AI-Database-Assistant.git
cd AI-Database-Assistant

# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your OpenAI API key

# Run
python main.py
```

Server starts at `http://localhost:8000` — API docs at `/docs`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/chat` | Conversational SQL help |
| `POST` | `/api/v1/analyze` | Deep SQL analysis & optimization |

### Chat Example

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I find duplicate emails in a users table?",
    "database_type": "postgresql"
  }'
```

### SQL Analysis Example

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sql_query": "SELECT * FROM users u JOIN orders o ON u.id = o.user_id WHERE UPPER(u.name) LIKE '\''%JOHN%'\'' ORDER BY o.created_at",
    "database_type": "postgresql"
  }'
```

Returns: formatted SQL, detected issues, optimized query, index suggestions.

## Static Analysis (No AI Required)

The SQL analyzer catches common anti-patterns without any API calls:

- `SELECT *` usage
- `UPDATE`/`DELETE` without `WHERE`
- Leading wildcards in `LIKE` (kills indexes)
- `ORDER BY` without `LIMIT`
- `DISTINCT` with `JOIN` (often masks join issues)
- Functions in `WHERE` clause (prevents index usage)
- Index recommendations based on query structure

## Project Structure

```
aquafold-db-assistant/
├── main.py                    # FastAPI entry point
├── config/
│   └── settings.py            # Centralized env-based config
├── src/
│   ├── api/
│   │   └── routes.py          # API endpoints
│   ├── core/
│   │   ├── sql_analyzer.py    # Static SQL analysis engine
│   │   └── prompts.py         # AI prompt templates
│   ├── models/
│   │   └── schemas.py         # Pydantic request/response models
│   └── services/
│       └── ai_service.py      # AI provider integration
├── tests/
│   ├── test_sql_analyzer.py   # 15 unit tests for static analysis
│   └── test_api.py            # 7 API endpoint tests
├── requirements.txt
├── .env.example
└── LICENSE
```

## Tech Stack

- **Python 3.9+** — Runtime
- **FastAPI** — Async API framework
- **OpenAI API** — AI-powered analysis
- **sqlparse** — SQL parsing and formatting
- **Pydantic v2** — Data validation
- **pytest** — Test suite (22 tests)

## Running Tests

```bash
python -m pytest tests/ -v
```

All 22 tests pass without requiring an API key — static analysis and API validation tests run offline.

## Use Cases

- **Database IDE Integration** — Embed as a backend service for SQL IDEs
- **Developer Onboarding** — Help new team members write better SQL
- **Code Review** — Automated SQL review in CI/CD pipelines
- **Performance Tuning** — Quick analysis of slow queries

## License

MIT — see [LICENSE](LICENSE).

## Contact

**Escipion Pedroza**  
GitHub: [@escipionpedroza147-commits](https://github.com/escipionpedroza147-commits)
