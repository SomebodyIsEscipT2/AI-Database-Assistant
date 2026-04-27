# Contributing to AI Database Assistant

Thanks for your interest in contributing! This guide will help you get started.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/escipionpedroza147-commits/AI-Database-Assistant.git
cd AI-Database-Assistant

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env with your settings (OPENAI_API_KEY is optional for development)
```

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
pip install coverage
coverage run -m pytest tests/ -v
coverage report --show-missing

# Run a specific test file
python -m pytest tests/test_schema_analyzer.py -v
```

All tests run **offline** — no API keys required. Tests that touch AI features gracefully handle missing keys.

## Project Structure

- `src/core/` — Analysis engines (SQL, schema, comparison)
- `src/api/` — FastAPI route handlers
- `src/models/` — Pydantic request/response schemas
- `src/services/` — Business logic and external integrations
- `tests/` — Test suite (pytest)
- `config/` — Application configuration

## How to Contribute

### Reporting Bugs

Open an issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Database type and version (if relevant)
- Python version and OS

### Suggesting Features

Open an issue with the `enhancement` label. Include:
- Use case description
- Proposed API design (if applicable)
- Example input/output

### Submitting Code

1. **Fork** the repository
2. **Create a feature branch** (`git checkout -b feature/my-feature`)
3. **Write tests** for new functionality
4. **Run the full test suite** and ensure all tests pass
5. **Submit a PR** with a clear description of what changed and why

### Code Style

- **Type hints** on all function signatures
- **Docstrings** on all public functions and classes
- **Comments** explain the "why", not the "what"
- **Keep functions small** and focused on a single responsibility
- **Follow existing patterns** — look at similar code in the project

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add query comparison endpoint
fix: handle empty SQL in schema analyzer
docs: update API endpoint documentation
test: add edge case tests for token counting
ci: add Python 3.12 to test matrix
```

### PR Checklist

- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Type hints on all new functions
- [ ] Docstrings on all new public functions
- [ ] README updated if adding new endpoints or features
- [ ] No secrets or API keys in committed code

## Architecture Decisions

- **Static analysis first** — Always provide value without AI (offline mode)
- **Graceful degradation** — If AI is unavailable, return static results
- **Type safety** — Pydantic models for all API boundaries
- **Test offline** — All tests work without external dependencies

## Need Help?

Open an issue or reach out to [@escipionpedroza147-commits](https://github.com/escipionpedroza147-commits).
