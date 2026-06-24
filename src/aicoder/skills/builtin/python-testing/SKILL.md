---
name: python-testing
description: Python testing best practices with pytest for writing and running tests, including fixtures, mocking, parametrization, and async patterns.
---

# Python Testing

## When to Use
- Writing unit tests for Python code
- Setting up test fixtures and conftest
- Mocking external dependencies
- Testing async code

## Instructions

### Test Framework
Use pytest. Tests go in `tests/` directory, files named `test_*.py`.

### Fixtures
Define reusable fixtures in `conftest.py`.
```python
@pytest.fixture
def sample_data():
    return {"key": "value"}
```

### Mocking
Use `unittest.mock` for mocking. Use `AsyncMock` for async dependencies.

### Running Tests
```bash
pytest tests/              # All tests
pytest tests/test_x.py -v  # Single test
pytest --cov=src tests/    # With coverage
```
