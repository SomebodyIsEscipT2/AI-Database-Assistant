# Contributing

Contributions are welcome! Here's how to get started:

## Development Setup

```bash
git clone https://github.com/escipionpedroza147-commits/AI-Database-Assistant.git
cd AI-Database-Assistant
pip install -r requirements.txt
cp .env.example .env
```

## Running Tests

```bash
python -m pytest tests/ -v
```

All tests should pass without an API key (static analysis tests are offline).

## Pull Request Process

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a PR with a clear description

## Code Style

- Python type hints on all function signatures
- Docstrings on all public functions
- Comment the "why", not the "what"
- Keep functions small and testable

## Reporting Issues

Open an issue with:
- What you expected
- What happened
- Steps to reproduce
- Database type and version (if relevant)
