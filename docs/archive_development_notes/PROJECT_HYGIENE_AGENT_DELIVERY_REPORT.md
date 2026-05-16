# Project Hygiene Agent Delivery Report

Version delivered: ProjectHygiene v1.0

## Scope

This hygiene pass fixed project-level test architecture, cache hygiene, Git/CI
readiness, legacy-script documentation, requirements reproducibility, and
minimal retriever tests.

No ESG extraction logic, output contracts, PDFs, business outputs, or scoring
behavior were intentionally changed.

## Delivered Changes

- Added reproducible hygiene audit tooling:
  - `tools/project_hygiene_audit.py`
  - `project_hygiene_outputs/project_hygiene_report.json`
  - `project_hygiene_outputs/project_hygiene_findings.jsonl`
  - `project_hygiene_outputs/project_hygiene_report.md`
- Fixed test helper collisions:
  - converted `from helpers import ...` to `from .helpers import ...`
  - added test package `__init__.py` files
  - added `pytest.ini` with importlib import mode and writable cache path
  - added `tools/check_test_helper_imports.py`
- Added safe Python cache tooling:
  - `tools/clean_python_artifacts.py`
  - dry-run by default, `--execute` required for deletion
- Added Git/CI readiness docs:
  - `.gitignore`
  - `GIT_SETUP_GUIDE.md`
- Documented legacy scripts:
  - `LEGACY_SCRIPTS.md`
  - explicit warning in `run_extraction_test.py`
- Bounded requirements and added dependency docs:
  - `requirements-dev.txt`
  - `REQUIREMENTS_NOTES.md`
  - `tools/check_requirements.py`
- Added non-network retriever tests for `AnnualReportRetriever`.
- Added project validation runner:
  - `tools/run_project_validation.py`
  - `PROJECT_VALIDATION.md`

## Validation Summary

- `python -m pytest --basetemp .pytest_tmp/final_global_cache`: `384 passed`
- `python tools/run_project_validation.py --project-root . --full`: `14/14 passed`
- `python -m compileall -q ...`: passed
- `python tools/check_test_helper_imports.py --project-root .`: passed
- `python tools/check_requirements.py --project-root .`: passed

## Notes

The retriever test expansion is intentionally partial: `AnnualReportRetriever`
now has meaningful non-network coverage and
`RETRIEVER_TEST_COVERAGE_REPORT.md` documents the remaining retrievers.
