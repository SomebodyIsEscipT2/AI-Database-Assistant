# 🗄️ AI Database Assistant

> AI-powered SQL optimization, query debugging, schema analysis, and database administration assistant.  
> Built for multi-platform database environments — PostgreSQL, MySQL, SQL Server, Oracle.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/escipionpedroza147-commits/AI-Database-Assistant/actions/workflows/tests.yml/badge.svg)](https://github.com/escipionpedroza147-commits/AI-Database-Assistant/actions/workflows/tests.yml)
[![Tests](https://img.shields.io/badge/tests-79%20passed-brightgreen.svg)]()
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg?logo=docker)](Dockerfile)

## What It Does

A production-grade AI assistant that helps database professionals:

- **🔍 Write SQL** — Describe what you need in plain English, get optimized queries
- **🐛 Debug queries** — Paste broken SQL and get explanations + fixes
- **⚡ Optimize performance** — Static analysis + AI-powered suggestions for indexes, rewrites, and execution plan improvements
- **📊 Explain execution plans** — Turn cryptic EXPLAIN output into plain English
- **🗂️ Analyze schemas** — Detect indexing opportunities, normalization issues, and anti-patterns in CREATE TABLE statements
- **🔄 Compare queries** — Side-by-side diff of original vs optimized queries with token counts and issue tracking
- **📈 Track history** — Log every analysis with aggregate stats and trends
- **🌐 Multi-database** — PostgreSQL, MySQL, SQL Server, Oracle with dialect-aware suggestions

## Quick Start

### Local Development

```bash
# Clone
git clone https://github.com/escipionpedroza147-commits/AI-Database-Assistant.git
cd AI-Database-Assistant

# Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your OpenAI API key

# Run
python main.py
```

Server starts at `http://localhost:8000` — API docs at `/docs`.

### Docker

```bash
# Build and run
docker-compose up -d

# Or standalone
docker build -t ai-db-assistant .
docker run -p 8000:8000 --env-file .env ai-db-assistant
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check / liveness probe |
| `POST` | `/api/v1/chat` | Conversational SQL help |
| `POST` | `/api/v1/analyze` | Deep SQL analysis & optimization |
| `POST` | `/api/v1/schema/analyze` | Database schema analysis |
| `POST` | `/api/v1/compare` | Query comparison (original vs optimized) |
| `GET` | `/api/v1/history` | Query analysis history (paginated) |
| `GET` | `/api/v1/history/stats` | Aggregate analytics & statistics |

### Chat — Conversational SQL Help

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I find duplicate emails in a users table?",
    "database_type": "postgresql"
  }'
```

### SQL Analysis — Deep Query Optimization

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sql_query": "SELECT * FROM users u JOIN orders o ON u.id = o.user_id WHERE UPPER(u.name) LIKE '\''%JOHN%'\'' ORDER BY o.created_at",
    "database_type": "postgresql"
  }'
```

Returns: formatted SQL, detected issues, optimized query, index suggestions.

### Schema Analysis — DDL Review

```bash
curl -X POST http://localhost:8000/api/v1/schema/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "schema_sql": "CREATE TABLE orders (id INT, user_id INT, total FLOAT, status TEXT, FOREIGN KEY (user_id) REFERENCES users(id));",
    "database_type": "postgresql"
  }'
```

Returns: table count, issues (indexing, normalization, anti-patterns), suggestions.

### Query Comparison — Before vs After

```bash
curl -X POST http://localhost:8000/api/v1/compare \
  -H "Content-Type: application/json" \
  -d '{
    "original_query": "SELECT * FROM users WHERE UPPER(name) = '\''JOHN'\'' ORDER BY created_at",
    "optimized_query": "SELECT id, name FROM users WHERE name = '\''JOHN'\'' ORDER BY created_at LIMIT 100"
  }'
```

Returns: token counts, reduction %, structural diff, resolved/new issues.

### Analytics — Query History & Stats

```bash
# Get analysis history (paginated)
curl "http://localhost:8000/api/v1/history?limit=20&offset=0"

# Get aggregate statistics
curl http://localhost:8000/api/v1/history/stats
```

## Static Analysis (No AI Required)

The SQL analyzer catches common anti-patterns without any API calls:

- `SELECT *` usage
- `UPDATE`/`DELETE` without `WHERE`
- Leading wildcards in `LIKE` (kills indexes)
- `ORDER BY` without `LIMIT`
- `DISTINCT` with `JOIN` (often masks join issues)
- Functions in `WHERE` clause (prevents index usage)
- Index recommendations based on query structure

The schema analyzer detects:

- Missing primary keys
- Unindexed foreign key columns
- `FLOAT`/`DOUBLE` for monetary values (precision loss)
- `TEXT` for enum-like fields
- `VARCHAR(255)` as thoughtless default
- Nullable boolean columns (three-valued logic)
- Repeated column patterns (normalization issues)
- Wide tables (20+ columns)

## Architecture

```
aquafold-db-assistant/
├── main.py                         # FastAPI entry point + CORS + logging
├── config/
│   └── settings.py                 # Centralized env-based config (Pydantic)
├── src/
│   ├── api/
│   │   └── routes.py               # 7 API endpoints
│   ├── core/
│   │   ├── sql_analyzer.py         # Static SQL analysis engine
│   │   ├── schema_analyzer.py      # DDL parser + schema analysis
│   │   ├── query_comparator.py     # Query diff + comparison engine
│   │   └── prompts.py              # AI prompt templates
│   ├── models/
│   │   └── schemas.py              # Pydantic request/response models
│   └── services/
│       ├── ai_service.py           # AI provider integration (OpenAI)
│       └── query_history.py        # In-memory query history store
├── tests/
│   ├── test_api.py                 # API endpoint tests
│   ├── test_sql_analyzer.py        # Static analysis unit tests
│   ├── test_schema_analyzer.py     # Schema analyzer tests
│   ├── test_query_comparator.py    # Query comparison tests
│   └── test_query_history.py       # History store + analytics tests
├── .github/
│   └── workflows/
│       └── tests.yml               # CI: Python 3.10-3.12, coverage
├── Dockerfile                      # Multi-stage production build
├── docker-compose.yml              # One-command deployment
├── requirements.txt
├── .env.example
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
└── LICENSE
```

## Tech Stack

- **Python 3.10+** — Runtime
- **FastAPI** — Async API framework
- **OpenAI API** — AI-powered analysis (optional — static analysis works offline)
- **sqlparse** — SQL parsing and formatting
- **Pydantic v2** — Data validation and serialization
- **pytest** — Test suite (79 tests, 80%+ coverage)
- **Docker** — Containerized deployment
- **GitHub Actions** — CI/CD pipeline

## Running Tests

```bash
# All tests (no API key needed)
python -m pytest tests/ -v

# With coverage
pip install coverage
coverage run -m pytest tests/ -v
coverage report --show-missing
```

All 79 tests pass without requiring an API key — static analysis, schema analysis, query comparison, history, and API validation tests all run offline.

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI API key (required for AI features) |
| `OPENAI_MODEL` | `gpt-4o` | Model to use for AI analysis |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `LOG_LEVEL` | `info` | Logging level |

## Use Cases

- **Database IDE Integration** — Embed as a backend service for SQL IDEs (AquaFold products)
- **Developer Onboarding** — Help new team members write better SQL
- **Code Review** — Automated SQL review in CI/CD pipelines
- **Performance Tuning** — Quick analysis of slow queries
- **Schema Reviews** — Catch issues before they hit production
- **Migration Planning** — Compare before/after query performance

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT — see [LICENSE](LICENSE).

## Contact

**Escipion Pedroza**  
GitHub: [@escipionpedroza147-commits](https://github.com/escipionpedroza147-commits)
