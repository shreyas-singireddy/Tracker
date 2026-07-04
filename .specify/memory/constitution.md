# FitOS Specification Constitution

## Principles

1. **Offline-First**: Zero network dependencies. All data is local SQLite.
2. **Privacy-by-Default**: No telemetry, no analytics, no external calls.
3. **Modularity**: Clear separation of concerns across layers.
4. **Testability**: Every component must be testable in isolation.
5. **Security**: Parameterized queries, no eval, no shell injection.

## Architecture Rules

- Models are dataclasses only — no business logic.
- Repositories handle only raw SQL — no business logic.
- Services contain all business logic.
- Modules wrap services and repositories.
- Registry handles dependency injection and lifecycle.
- UI is Streamlit-only — no separate frontend.

## Standards

- Python 3.11+
- Type hints on all public functions
- 80%+ test coverage
- Ruff formatting (120 char lines)
- AGPLv3 license
