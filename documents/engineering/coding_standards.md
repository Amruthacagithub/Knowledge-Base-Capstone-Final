# Coding Standards — TechNova Engineering

## Purpose

Consistent code style improves readability, reduces bugs, and makes code reviews faster. All engineers must follow these standards.

## Python Style Guide

- Follow **PEP 8** for Python code.
- Use **type hints** for all function signatures.
- Maximum line length: **120 characters**.
- Use **f-strings** for string formatting (not `.format()` or `%`).
- Write **docstrings** for all public functions and classes.

### Naming Conventions

```python
# Variables and functions: snake_case
user_count = 10
def get_user_by_id(user_id: str) -> User:
    ...

# Classes: PascalCase
class PaymentProcessor:
    ...

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
```

## Git Workflow

1. Create a feature branch from `main`: `feature/TICKET-123-add-search`
2. Keep commits small and focused. Each commit should do one thing.
3. Write meaningful commit messages: "Add permission filter to vector search" not "fix stuff"
4. Open a Pull Request with:
   - Description of what changed and why
   - Link to the relevant ticket
   - Screenshots for UI changes
5. Requires at least **1 approval** before merging.
6. Use **squash merge** to keep `main` history clean.

## Code Review Guidelines

- Review within **1 business day** of being requested.
- Be constructive — suggest improvements, don't just point out problems.
- Check for: correctness, edge cases, security, readability, and test coverage.

## Testing Requirements

- All new features must have unit tests.
- Aim for **80% code coverage** on new code.
- Integration tests for any new API endpoints.
- Run `pytest` before pushing: `python -m pytest tests/ -v`
