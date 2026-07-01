# Contributing to FitOS

Thank you for considering contributing to FitOS! We welcome contributions that improve the system.

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates.
2. Include a clear description, steps to reproduce, and expected vs actual behavior.
3. Include logs and screenshots if applicable.

### Suggesting Features

1. Describe the feature and its use case.
2. Explain how it aligns with FitOS's offline-first philosophy.
3. Be specific about the implementation approach.

### Pull Requests

1. Fork the repository.
2. Create a feature branch from `main`.
3. Make your changes following the project's coding standards.
4. Run all tests and lint checks before submitting.
5. Write clear commit messages following conventional commits.
6. Update documentation as needed.
7. Submit the PR with a clear description of changes.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/fitos.git
cd fitos

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest tests/
```

## Coding Standards

- **Python version**: 3.11+
- **Formatting**: Ruff (120 char line length)
- **Linting**: Ruff, Flake8, Pylint
- **Type checking**: Mypy
- **Security**: Bandit, Semgrep
- **Testing**: Pytest with coverage >= 80%

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new feature
fix: resolve bug in module
docs: update documentation
refactor: restructure code
test: add test coverage
chore: update dependencies
```

## Pull Request Checklist

- [ ] Code follows project style (ruff check passes)
- [ ] Type hints added (mypy passes)
- [ ] Tests pass with coverage >= 80%
- [ ] Documentation updated
- [ ] Security checks pass
- [ ] No secrets or credentials in code
