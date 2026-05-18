# Contributing Guidelines

**Language / 语言**: [🇺🇸 English](CONTRIBUTING.md) | [🇨🇳 中文](CONTRIBUTING_ZH.md)

---

## 🤝 Welcome to Contribute!

We welcome contributions of all kinds: code improvements, bug fixes, documentation enhancements, feature suggestions, and more!

---

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Standards](#code-standards)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)
- [Feature Requests](#feature-requests)

---

## 🚀 Getting Started

### 1. Fork the Repository

Click the "Fork" button at the top right of the repository page.

### 2. Clone Your Fork

```bash
git clone https://github.com/YOUR_USERNAME/nvidia-model-tester.git
cd nvidia-model-tester
```

### 3. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install development tools (optional)
pip install pytest black flake8 mypy
```

### 4. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

---

## 💻 Development Setup

### Project Structure

```
nvidia-model-tester/
├── main.py              # Entry point
├── config.py            # Configuration
├── models/              # Model management
├── tests/               # Test suites
├── scenarios/           # Test prompts
├── reporters/           # Report generation
├── utils/               # Utilities
└── output/              # Generated reports
```

### Running Tests Locally

```bash
# Quick test with sample models
python main.py --scope sample --concurrency 3

# Test specific category
python main.py --scope llm --max-models 5

# Skip quality evaluation for faster testing
python main.py --no-quality
```

### Code Quality Tools

```bash
# Format code with Black
black .

# Check style with Flake8
flake8 .

# Type checking with MyPy
mypy .
```

---

## 📝 Code Standards

### Python Style Guide

We follow **PEP 8** with these specifics:

- **Indentation**: 4 spaces (no tabs)
- **Line length**: Maximum 100 characters
- **Imports**: Grouped and sorted
  ```python
  # Standard library
  import os
  import sys
  
  # Third-party
  import httpx
  from pydantic import Field
  
  # Local modules
  from config import settings
  from utils.api_client import NIMClient
  ```

### Type Annotations

All functions should have type hints:

```python
def calculate_score(results: list[float], weight: float = 1.0) -> float:
    """Calculate weighted score.
    
    Args:
        results: List of raw scores
        weight: Weighting factor
        
    Returns:
        Weighted average score
    """
    return sum(r * weight for r in results) / len(results)
```

### Docstring Format

Use Google-style docstrings:

```python
class ModelTester:
    """Test runner for NVIDIA models.
    
    Attributes:
        client: API client instance
        timeout: Request timeout in seconds
    """
    
    def test_model(self, model: ModelInfo) -> TestResult:
        """Execute tests on a single model.
        
        Args:
            model: Model information object
            
        Returns:
            Test result with scores and details
            
        Raises:
            ConnectionError: If API is unreachable
        """
        pass
```

### Naming Conventions

- **Variables/Functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_CASE`
- **Private methods**: `_leading_underscore`

```python
MAX_CONCURRENCY = 50

def calculate_average(scores: list[float]) -> float:
    pass

class TestResult:
    pass

def _internal_helper():
    pass
```

---

## 🔧 Submitting Changes

### Commit Messages

Follow conventional commits format:

```
type(scope): description

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style (formatting, semicolons, etc)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(reporter): add bilingual support to HTML reports

fix(api-client): handle rate limit 429 errors with retry logic

docs(readme): update installation instructions

refactor(tests): extract common test logic into base class
```

### Pull Request Process

1. **Update your fork**
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/nvidia-model-tester.git
   git fetch upstream
   git merge upstream/main
   ```

2. **Push your branch**
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create Pull Request**
   - Go to the original repository
   - Click "New Pull Request"
   - Select your branch
   - Fill in the PR template

4. **PR Description Should Include**:
   - What changes were made
   - Why these changes are needed
   - How to test the changes
   - Any breaking changes
   - Related issues (e.g., "Fixes #123")

### Code Review Checklist

Before submitting, ensure:

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New features have tests
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] No debug code or comments
- [ ] Type hints are complete
- [ ] No sensitive data (API keys, etc.)

---

## 🐛 Reporting Issues

### Bug Report Template

When reporting bugs, include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**:
   ```
   1. Run command: python main.py --scope sample
   2. Observe error: ...
   ```
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**:
   - OS: Windows/Linux/Mac
   - Python version: 3.x.x
   - Package versions: (from `pip freeze`)
6. **Error Logs**: Full error traceback
7. **Screenshots**: If applicable

### Example Bug Report

```markdown
## Bug: Rate limiter not working with high concurrency

**Description**: When using --concurrency 20, getting 429 errors despite rate limiter.

**Steps to Reproduce**:
1. Set concurrency to 20
2. Run: python main.py --scope llm --concurrency 20
3. Observe multiple 429 errors

**Expected**: Rate limiter should prevent exceeding 40 req/min

**Actual**: Getting 429 errors after ~10 requests

**Environment**:
- OS: Ubuntu 22.04
- Python: 3.11.4
- httpx: 0.24.1

**Logs**:
```
⚠️ Rate limited (429), retrying...
```
```

---

## ✨ Feature Requests

### Feature Request Template

1. **Problem Statement**: What problem does this solve?
2. **Proposed Solution**: How should it work?
3. **Alternatives Considered**: Other approaches you've thought about
4. **Additional Context**: Examples, mockups, references

### Example Feature Request

```markdown
## Feature: Add JSON report export

**Problem**: Currently only HTML reports are generated, making programmatic analysis difficult.

**Solution**: Add option to export results as JSON:
- Command line flag: --format json
- Output file: output/report.json
- Include all metrics and scores

**Alternatives**:
- CSV export (less structured)
- Database storage (overkill for this use case)

**Use Case**: 
I want to analyze results across multiple test runs using pandas.
```

---

## 🧪 Testing Guidelines

### Writing Tests

If you add new functionality, include tests:

```python
def test_rate_limiter():
    """Test that rate limiter enforces limits."""
    limiter = RateLimiter(max_requests=5, window_seconds=1.0)
    
    # Record 5 requests
    for _ in range(5):
        limiter.record_request()
    
    # Should not allow 6th request immediately
    assert not limiter.can_make_request()
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_api_client.py

# Run with coverage
pytest --cov=. tests/
```

---

## 📚 Documentation

### Updating Documentation

When making changes:

1. **Code Comments**: Update inline comments if logic changes
2. **Docstrings**: Update function/class docstrings
3. **README**: Update usage examples if CLI changes
4. **Architecture**: Update if adding new modules

### Documentation Style

- Use clear, concise language
- Include code examples
- Link to related sections
- Keep examples up-to-date

---

## 🎯 Contribution Areas

### High Priority

- [ ] Add more test scenarios
- [ ] Improve error handling
- [ ] Enhance report visualizations
- [ ] Add unit tests

### Medium Priority

- [ ] Support additional model types
- [ ] Add caching for repeated tests
- [ ] Implement progress bars
- [ ] Add export to other formats (CSV, PDF)

### Low Priority

- [ ] Web UI for configuration
- [ ] Real-time dashboard
- [ ] Comparison mode between runs
- [ ] Plugin system for custom testers

---

## 🙏 Recognition

Contributors will be acknowledged in:

- README.md contributors section
- Release notes
- Special thanks in reports

---

## ❓ Questions?

- Check existing [Issues](https://github.com/.../issues)
- Read the [Documentation](README_EN.md)
- Ask in [Discussions](https://github.com/.../discussions)

---

## 📜 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Focus on what's best for the community

---

**Thank you for contributing!** 🎉

[🇨🇳 中文版](CONTRIBUTING_ZH.md) | [🇺🇸 English](CONTRIBUTING.md)
