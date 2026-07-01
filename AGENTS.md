# FitOS — Agent Knowledge Base

## Project Overview

FitOS is an offline-first AI fitness operating system built with Python and Streamlit. It uses SQLite for persistence and provides workout, nutrition, habit, recovery, and analytics tracking through a modular architecture.

## Architecture

```
app/
├── core/           # Configuration, logging, exceptions, bootloader
├── database/       # SQLite connection manager, migrations
├── models/         # Dataclass models (domain, workout, nutrition, etc.)
├── repositories/   # Data access layer (CRUD operations)
├── services/       # Business logic layer
├── modules/        # Module wrappers (Workout, Nutrition, etc.)
├── registry/       # Module registration and dependency resolution
├── ui/             # Streamlit UI (pages, components)
└── utils/          # Validators, performance utilities
```

## Key Patterns

- **Repository Pattern**: All database access goes through repositories.
- **Service Layer**: Business logic is in services.
- **Module System**: Each domain has a module that wraps repositories and services.
- **Dependency Injection**: Services receive repos via constructor injection.
- **Offline-First**: Zero network dependencies; all data is local SQLite.

## Tools Configuration

- **Ruff**: Formatting and linting (line-length: 120)
- **Mypy**: Type checking (strict mode disabled for Streamlit)
- **Flake8**: Additional linting
- **Pylint**: Code quality analysis
- **Bandit**: Security scanning
- **Vulture**: Dead code detection
- **Pytest**: Testing with coverage

## Pre-commit

```bash
pip install pre-commit
pre-commit install
```

## CI/CD

The GitLab CI pipeline includes stages for format, lint, type_check, test, coverage, security, and build.

## Testing

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

Maintain >= 80% code coverage.

## Security

- Bandit for Python security scanning
- Semgrep for static analysis
- pip-audit for dependency vulnerability scanning
- gitleaks for secrets detection
