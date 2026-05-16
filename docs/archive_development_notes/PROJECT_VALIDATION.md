# Project Validation

Use the project validation runner for CI-style hygiene checks.

Quick validation:

```powershell
python tools/run_project_validation.py --project-root . --quick
```

Full validation:

```powershell
python tools/run_project_validation.py --project-root . --full
```

The full mode runs:

- test helper import validation;
- requirements validation;
- `compileall` on core modules;
- isolated pytest for core modules;
- retriever pytest for `AnnualReportRetriever`;
- global pytest.

Reports are written to:

- `project_validation_summary.json`
- `project_validation_report.md`

The script does not run any ESG extraction pipeline and does not modify
business outputs.
