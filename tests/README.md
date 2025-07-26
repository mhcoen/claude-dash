# Claude Dash Test Suite

This directory contains comprehensive tests for Claude Dash.

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=claude_dash

# Run specific test file
pytest tests/unit/test_adaptive_bounds.py

# Run specific test
pytest tests/unit/test_adaptive_bounds.py::TestAdaptiveBoundsCalculator::test_initialization

# Run tests with verbose output
pytest -v

# Run only unit tests
pytest tests/unit -v

# Run only integration tests
pytest tests/integration -v
```

### Using the Test Runner Script

```bash
# Run the comprehensive test suite
./run_tests.sh
```

## Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_adaptive_bounds.py
│   ├── test_bayesian_limits.py
│   ├── test_claude_code_reader.py
│   └── test_config_manager.py
├── integration/             # Integration tests
│   └── test_end_to_end.py
├── fixtures/               # Test data and fixtures
│   └── sample_entries.py
└── conftest.py            # Pytest configuration and shared fixtures
```

## Writing Tests

### Unit Tests

Unit tests should:
- Test individual functions/methods in isolation
- Use mocks for external dependencies
- Be fast and deterministic
- Cover edge cases and error conditions

Example:
```python
def test_add_prompt_simple_pattern(self):
    calc = AdaptiveBoundsCalculator()
    calc.add_prompt(2)
    assert calc.pattern_history[0] == 'simple'
```

### Integration Tests

Integration tests should:
- Test complete workflows
- Use real file I/O where appropriate
- Verify component interactions
- Test realistic scenarios

Example:
```python
def test_full_data_pipeline(self, temp_claude_dir):
    reader = ClaudeCodeReader()
    session_info = reader.get_current_session_info()
    assert session_info['window_tokens'] > 0
```

## Coverage

To view detailed coverage report:

```bash
# Generate HTML coverage report
pytest --cov=claude_dash --cov-report=html

# Open in browser
open htmlcov/index.html
```

Current coverage targets:
- Unit tests: >80% coverage
- Integration tests: Key workflows covered
- Overall: >70% coverage

## Continuous Integration

Tests run automatically on:
- Every push to main branch
- Every pull request
- Multiple Python versions (3.9-3.12)
- Multiple platforms (Linux, macOS, Windows)

See `.github/workflows/tests.yml` for CI configuration.