# Contributing to ESG-Pipeline

Thank you for your interest in contributing to **ESG-Pipeline**! 🙌 We welcome contributions from developers, data scientists, and domain experts. This guide will help you get started.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing Requirements](#testing-requirements)
- [Code Style & Quality](#code-style--quality)
- [Commit & PR Guidelines](#commit--pr-guidelines)
- [Adding a New Retriever](#adding-a-new-retriever)
- [Reporting Bugs](#reporting-bugs)
- [Documentation](#documentation)
- [License](#license)

---

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please:

- Be respectful and inclusive in all interactions
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn and grow

---

## Getting Started

### Prerequisites

- Python 3.9 or later
- Git
- pip or conda
- GitHub account

### Fork & Clone

1. Fork the repository: https://github.com/Ensea-upb/ESG-Pipeline
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR-USERNAME/ESG-Pipeline.git
   cd ESG-Pipeline
   ```
3. Add upstream remote:
   ```bash
   git remote add upstream https://github.com/Ensea-upb/ESG-Pipeline.git
   ```

---

## Development Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install in Development Mode

```bash
# Install base dependencies + dev tools
pip install -e ".[dev]"

# Optional: ML dependencies for advanced extraction
pip install -e ".[dev,ml]"
```

### 3. Install Pre-commit Hooks (Optional but Recommended)

```bash
pre-commit install
```

This will automatically run code formatters and linters on every commit.

### 4. Verify Installation

```bash
# Run tests
pytest tests/ -v

# Check code style
black --check .
flake8 .
mypy AnnualReportRetriever/ --ignore-missing-imports
```

---

## Making Changes

### 1. Create a Feature Branch

Always create a new branch for your changes:

```bash
# Update main first
git checkout main
git fetch upstream
git rebase upstream/main

# Create feature branch
git checkout -b feature/your-feature-name
# or for bug fixes
git checkout -b fix/bug-description
```

### 2. Make Your Changes

```bash
# Edit files
code path/to/file.py

# Add your changes
git add .

# Commit (see Commit Guidelines below)
git commit -m "feat: add new document retriever"
```

### 3. Run Tests & Code Quality Checks

```bash
# Run all tests
pytest tests/ -v --cov

# Format code
black .
isort .

# Check linting
flake8 .
mypy . --ignore-missing-imports

# Check for security issues
bandit -r . -ll
```

### 4. Push & Create Pull Request

```bash
git push origin feature/your-feature-name
```

Go to GitHub and create a Pull Request. Use the PR template provided.

---

## Testing Requirements

We aim for **80% code coverage minimum** for new code.

### Writing Tests

Tests go in `tests/` directory, organized by module:

```
tests/
├── test_annual_report_retriever.py
├── test_esg_extraction.py
├── test_validation.py
└── fixtures/
    └── sample_pdfs/
```

### Test Example

```python
import pytest
from AnnualReportRetriever.retriever import AnnualReportRetriever

@pytest.mark.unit
def test_annual_report_download():
    """Test downloading annual report for a known company."""
    retriever = AnnualReportRetriever()
    result = retriever.search(
        company_name="Apple Inc.",
        fiscal_year=2024,
        official_domain="apple.com"
    )
    assert result is not None
    assert len(result) > 0

@pytest.mark.integration
def test_end_to_end_extraction():
    """Test full extraction pipeline."""
    # ... integration test
    pass
```

### Run Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_retriever.py -v

# With coverage
pytest --cov=. tests/ --cov-report=html

# Only unit tests
pytest -m unit

# Only fast tests
pytest -m "not slow"
```

---

## Code Style & Quality

### Python Code Style (PEP 8)

We use **Black** for formatting and **isort** for import sorting.

```bash
# Auto-format all files
black .
isort .

# Check without formatting
black --check .
```

### Type Hints

Use type hints for all new functions:

```python
from typing import Optional, List, Dict

def extract_indicators(
    pdf_path: str,
    company_name: str,
    fiscal_year: int,
) -> Dict[str, Optional[str]]:
    """Extract ESG indicators from a PDF.
    
    Args:
        pdf_path: Path to the PDF file
        company_name: Name of the company
        fiscal_year: Fiscal year
        
    Returns:
        Dictionary mapping indicator keys to values
    """
    # Implementation
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def my_function(arg1: str, arg2: int) -> bool:
    """Short description.
    
    Longer description explaining what the function does, 
    edge cases, and any important behavior.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When arg2 is negative
        
    Example:
        >>> result = my_function("test", 42)
        >>> print(result)
        True
    """
    if arg2 < 0:
        raise ValueError("arg2 must be non-negative")
    return True
```

### Linting & Type Checking

```bash
# Pylint
pylint AnnualReportRetriever/ --exit-zero

# Flake8
flake8 AnnualReportRetriever/

# MyPy (type checking)
mypy AnnualReportRetriever/ --ignore-missing-imports
```

---

## Commit & PR Guidelines

### Commit Messages

We follow **Conventional Commits** format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style (formatting, missing semicolons, etc.)
- `refactor:` Code refactoring without functional changes
- `perf:` Performance improvements
- `test:` Adding or updating tests
- `chore:` Build, dependencies, tooling

**Examples:**

```bash
git commit -m "feat(AnnualReportRetriever): add PDF quality scoring"
git commit -m "fix(ESGExtraction): resolve encoding issue with non-ASCII chars"
git commit -m "docs: update README with architecture diagram"
git commit -m "test(validation): add unit tests for indicator schema"
```

### Pull Request Template

When creating a PR, use this template:

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change
- [ ] Documentation

## Related Issues
Closes #123

## Testing
- [ ] Added unit tests
- [ ] Added integration tests
- [ ] Tests pass locally
- [ ] Coverage maintained (80%+)

## Checklist
- [ ] Code follows project style
- [ ] Documentation updated
- [ ] No new warnings introduced
- [ ] Commits are squashed and descriptive
```

---

## Adding a New Retriever

Want to add support for a new document type? Here's how:

### 1. Create Module Structure

```bash
mkdir NewDocumentRetriever
cd NewDocumentRetriever

# Create directory structure
mkdir -p scripts data/dossier_ingestion_0
touch __init__.py
touch retriever.py
touch config.yaml
```

### 2. Implement Retriever Class

```python
# NewDocumentRetriever/retriever.py

from typing import List, Dict, Optional
from pathlib import Path
import requests
from pydantic import BaseModel, Field

class RetrievalConfig(BaseModel):
    """Configuration for the retriever."""
    company_name: str
    fiscal_year: int
    official_domain: str

class DocumentCandidate(BaseModel):
    """A potential document match."""
    url: str
    title: str
    score: int = Field(..., ge=0, le=100)
    source: str
    retrieved_at: str

class NewDocumentRetriever:
    """Retrieves NewDocumentType from web sources."""
    
    def __init__(self, max_results: int = 20):
        self.max_results = max_results
        
    def search(
        self,
        company_name: str,
        fiscal_year: int,
        official_domain: str,
    ) -> List[DocumentCandidate]:
        """Search for documents.
        
        Args:
            company_name: Name of the company
            fiscal_year: Target fiscal year
            official_domain: Official company domain
            
        Returns:
            List of candidate documents ranked by relevance
        """
        # Implementation
        pass
        
    def download(self, url: str, output_path: Path) -> bool:
        """Download a document.
        
        Args:
            url: Document URL
            output_path: Where to save the file
            
        Returns:
            True if successful, False otherwise
        """
        # Implementation
        pass
```

### 3. Create Configuration

```yaml
# NewDocumentRetriever/config.yaml

retriever:
  name: "NewDocumentRetriever"
  description: "Retrieves new document type"
  document_types:
    - "PDF"
  

search_strategy:
  # Keywords specific to this document type
  strong_keywords:
    - "keyword1"
    - "keyword2"
  secondary_keywords:
    - "keyword3"

# Scoring system
scoring:
  strong_keyword_match: 40
  secondary_keyword_match: 20
  year_found: 20
  company_name_detected: 20
  official_domain: 20
  direct_pdf_url: 10
  company_name_absent: -40
```

### 4. Add Unit Tests

```python
# tests/test_new_document_retriever.py

import pytest
from NewDocumentRetriever.retriever import NewDocumentRetriever, DocumentCandidate

@pytest.mark.unit
class TestNewDocumentRetriever:
    
    @pytest.fixture
    def retriever(self):
        return NewDocumentRetriever()
    
    def test_search_returns_candidates(self, retriever):
        """Test that search returns candidate documents."""
        results = retriever.search(
            company_name="Apple Inc.",
            fiscal_year=2024,
            official_domain="apple.com"
        )
        assert isinstance(results, list)
        assert all(isinstance(r, DocumentCandidate) for r in results)
    
    def test_candidates_ranked_by_score(self, retriever):
        """Test that results are sorted by score."""
        results = retriever.search("Apple Inc.", 2024, "apple.com")
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)
    
    def test_download_creates_file(self, retriever, tmp_path):
        """Test that download creates output file."""
        url = "https://example.com/document.pdf"
        output = tmp_path / "document.pdf"
        
        success = retriever.download(url, output)
        if success:
            assert output.exists()
```

### 5. Add to CLI Script

```python
# NewDocumentRetriever/scripts/run_download_all.py

import argparse
from pathlib import Path
from NewDocumentRetriever.retriever import NewDocumentRetriever

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--company-name", required=True)
    parser.add_argument("--fiscal-year", type=int, required=True)
    parser.add_argument("--official-domain", required=True)
    
    args = parser.parse_args()
    
    retriever = NewDocumentRetriever()
    results = retriever.search(
        company_name=args.company_name,
        fiscal_year=args.fiscal_year,
        official_domain=args.official_domain,
    )
    
    print(f"Found {len(results)} candidates")
    for r in results:
        print(f"  [{r.score:3d}] {r.title} ({r.source})")

if __name__ == "__main__":
    main()
```

### 6. Update Documentation

Add an entry to the main README.md:

```markdown
| **NewDocumentRetriever** | New document type | Your scoring strategy |
```

### 7. Submit Pull Request

- Ensure all tests pass: `pytest tests/test_new_document_retriever.py`
- Check coverage: `pytest --cov=NewDocumentRetriever`
- Format code: `black . && isort .`
- Create PR with description

---

## Reporting Bugs

### Bug Report Template

```markdown
## Description
Clear description of the bug

## Steps to Reproduce
1. Step 1
2. Step 2
3. Step 3

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- Python version: 3.10
- OS: Ubuntu 22.04
- Branch: main

## Error Message / Stack Trace
```
<paste full error>
```

## Additional Context
Any other relevant info
```

Go to [Issues](https://github.com/Ensea-upb/ESG-Pipeline/issues) and create a new issue.

---

## Documentation

### Updating README

- Keep high-level overview in main README.md
- Detailed docs go in `docs/` folder
- Update examples if behavior changes
- Add diagrams for complex flows

### Writing Documentation

Use Markdown format with clear headings:

```markdown
# Topic Title

## Overview
Brief introduction

## How It Works
Detailed explanation

## Example
```python
# Code example
```

## See Also
- Related section
- Another resource
```

---

## Review Process

1. **CI Checks** — All automated tests must pass
2. **Code Review** — At least one maintainer reviews
3. **Approval** — PR approved by maintainer
4. **Merge** — Squash and merge to main

### What Reviewers Look For

- ✅ Code follows style guidelines
- ✅ Tests are comprehensive (80%+ coverage)
- ✅ Documentation is clear
- ✅ No performance regressions
- ✅ Commits are clean and descriptive

---

## Useful Resources

- **Python PEP 8 Style Guide**: https://pep8.org/
- **Conventional Commits**: https://www.conventionalcommits.org/
- **GitHub Docs**: https://docs.github.com/
- **Pytest Documentation**: https://docs.pytest.org/
- **Pydantic Documentation**: https://docs.pydantic.dev/

---

## Questions?

- Check existing [Issues](https://github.com/Ensea-upb/ESG-Pipeline/issues)
- Read the [README.md](README.md)
- Review module-specific README files
- Ask on GitHub Discussions

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing to ESG-Pipeline! 🚀
