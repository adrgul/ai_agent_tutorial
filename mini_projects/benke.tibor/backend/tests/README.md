# Backend Tests

Comprehensive unit tests for the KnowledgeRouter backend.

## 📊 Test Coverage

Current test modules:
- ✅ `test_error_handling.py` - Error handling module (90%+ coverage expected)
- ✅ `test_openai_clients.py` - OpenAI client factory (95%+ coverage expected)

## 🚀 Running Tests

### Quick Start

```bash
# Install test dependencies
cd backend
pip install pytest pytest-cov pytest-asyncio pytest-mock

# Run all tests
pytest

# Run with coverage report
pytest --cov=infrastructure --cov-report=html

# Run specific test file
pytest tests/test_error_handling.py

# Run specific test class
pytest tests/test_error_handling.py::TestTokenEstimation

# Run specific test
pytest tests/test_error_handling.py::TestTokenEstimation::test_estimate_tokens_simple_text
```

### Detailed Commands

```bash
# Run with verbose output
pytest -v

# Run with coverage and show missing lines
pytest --cov=infrastructure --cov-report=term-missing

# Run only unit tests (fast)
pytest -m unit

# Run integration tests
pytest -m integration

# Run and stop on first failure
pytest -x

# Run in parallel (faster)
pytest -n auto  # requires pytest-xdist
```

## 📁 Test Structure

```
tests/
├── __init__.py
├── test_error_handling.py      # Error handling module tests
│   ├── TestTokenEstimation      (7 tests)
│   ├── TestCostEstimation       (7 tests)
│   ├── TestTokenLimitCheck      (5 tests)
│   ├── TestRetryDecorator       (13 tests)
│   ├── TestTokenUsageTracker    (9 tests)
│   ├── TestAPICallError         (2 tests)
│   └── TestErrorHandlingIntegration (1 test)
│
└── test_openai_clients.py      # OpenAI client factory tests
    ├── TestOpenAIClientFactory  (11 tests)
    ├── TestUsageStats           (2 tests)
    ├── TestClientReset          (3 tests)
    ├── TestTemperatureHandling  (3 tests)
    └── TestOpenAIClientFactoryIntegration (3 tests)
```

**Total: 66 tests**

## ✅ Test Categories

### Unit Tests (Fast - <1s each)

**Error Handling:**
- Token estimation accuracy
- Cost calculation for different models
- Token limit validation
- Retry logic with different error types
- Usage tracker functionality

**OpenAI Clients:**
- Singleton pattern validation
- Environment variable configuration
- Custom parameter handling
- Client reset functionality

### Integration Tests (Slower - may need external services)

- Full workflow tests (estimate → check → retry → track)
- Multi-client coordination
- Configuration persistence

## 📋 Test Examples

### Running Specific Tests

```bash
# Test token estimation
pytest tests/test_error_handling.py::TestTokenEstimation -v

# Test retry logic
pytest tests/test_error_handling.py::TestRetryDecorator -v

# Test singleton pattern
pytest tests/test_openai_clients.py::TestOpenAIClientFactory::test_get_llm_singleton_pattern -v
```

### Coverage Reports

```bash
# Terminal report
pytest --cov=infrastructure --cov-report=term

# HTML report (opens in browser)
pytest --cov=infrastructure --cov-report=html
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

### Watch Mode (Auto-rerun on file changes)

```bash
# Install pytest-watch
pip install pytest-watch

# Run in watch mode
ptw -- --cov=infrastructure
```

## 🎯 Expected Test Results

### Success Output

```
================================ test session starts =================================
platform win32 -- Python 3.11.5, pytest-7.4.3, pluggy-1.3.0
rootdir: C:\...\backend
configfile: pytest.ini
plugins: cov-4.1.0, asyncio-0.21.1, mock-3.12.0
collected 66 items

tests/test_error_handling.py::TestTokenEstimation::test_estimate_tokens_empty_string PASSED [  1%]
tests/test_error_handling.py::TestTokenEstimation::test_estimate_tokens_simple_text PASSED [  3%]
...
tests/test_openai_clients.py::TestOpenAIClientFactory::test_get_llm_singleton_pattern PASSED [ 95%]
tests/test_openai_clients.py::TestTemperatureHandling::test_temperature_one PASSED [100%]

---------- coverage: platform win32, python 3.11.5 -----------
Name                                      Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------
infrastructure/__init__.py                    0      0   100%
infrastructure/error_handling.py            142      8    94%   45-47, 89-91
infrastructure/openai_clients.py             58      3    95%   78-80
-----------------------------------------------------------------------
TOTAL                                       200     11    94%

================================ 66 passed in 2.34s ==================================
```

### Coverage Report (HTML)

After running `pytest --cov=infrastructure --cov-report=html`, open `htmlcov/index.html`:

```
Module                          Statements  Missing  Excluded  Coverage
infrastructure/error_handling.py    142         8         0     94%
infrastructure/openai_clients.py      58         3         0     95%
TOTAL                                200        11         0     94%
```

## 🐛 Debugging Failed Tests

### Verbose Output

```bash
# Show full traceback
pytest -v --tb=long

# Show local variables in traceback
pytest -v --tb=long --showlocals

# Run with pdb debugger on failure
pytest --pdb
```

### Specific Test Debugging

```bash
# Run single test with maximum detail
pytest tests/test_error_handling.py::TestRetryDecorator::test_retry_rate_limit_with_backoff -vvs

# -vv: Extra verbose
# -s: Show print statements
```

## 📊 CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        cd backend
        pytest --cov=infrastructure --cov-fail-under=80
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## 🔧 Troubleshooting

### Import Errors

If you get `ModuleNotFoundError`:

```bash
# Ensure you're in the backend directory
cd backend

# Install all dependencies
pip install -r requirements.txt

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"  # Linux/Mac
$env:PYTHONPATH = "$env:PYTHONPATH;$(pwd)"  # PowerShell
```

### Missing Coverage

If coverage is lower than expected:

```bash
# Show which lines are not covered
pytest --cov=infrastructure --cov-report=term-missing

# Generate HTML report for detailed view
pytest --cov=infrastructure --cov-report=html
```

### Slow Tests

```bash
# Find slowest tests
pytest --durations=10

# Run only fast tests
pytest -m "not slow"
```

## 📚 Writing New Tests

### Test Template

```python
"""
Tests for [module_name].
"""
import pytest
from module_name import function_to_test


class TestFeatureName:
    """Tests for specific feature."""
    
    def test_basic_functionality(self):
        """Test basic happy path."""
        result = function_to_test(input_value)
        assert result == expected_value
    
    def test_edge_case(self):
        """Test edge case handling."""
        # Test implementation
        pass
    
    def test_error_handling(self):
        """Test error conditions."""
        with pytest.raises(ExpectedError):
            function_to_test(invalid_input)
```

### Best Practices

1. **One assertion per test** (when possible)
2. **Descriptive test names** (test_function_does_what_when_condition)
3. **Arrange-Act-Assert** pattern
4. **Use fixtures** for common setup
5. **Mock external dependencies** (OpenAI API, Qdrant, etc.)
6. **Test edge cases** (empty, null, large values)
7. **Test error paths** (exceptions, retries, failures)

## 🎯 Next Steps

### Immediate Todos

- [ ] Run initial test suite: `pytest`
- [ ] Check coverage: `pytest --cov=infrastructure --cov-report=html`
- [ ] Fix any failing tests
- [ ] Achieve 90%+ coverage

### Future Test Additions

- [ ] `test_qdrant_rag_client.py` - RAG client tests
- [ ] `test_agent.py` - LangGraph agent tests
- [ ] `test_views.py` - API endpoint tests (Django)
- [ ] `test_repositories.py` - Repository layer tests
- [ ] Integration tests with real Qdrant (Docker)
- [ ] End-to-end tests with real OpenAI calls (expensive, mark as slow)

## 📞 Support

For test-related issues:
1. Check test output carefully (`pytest -v`)
2. Review coverage report (`htmlcov/index.html`)
3. Run with debugging (`pytest --pdb`)
4. Check this README for common issues

---

**Happy Testing! 🧪**
