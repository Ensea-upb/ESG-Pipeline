# Git Setup Guide

This project can be prepared for Git without committing generated data.

## Initialize Git

If the project is not already a repository:

```powershell
git init
git status --short
```

Do not create a commit until `git status --short` shows only source code,
tests, documentation, contracts, and small configuration files that should be
tracked.

## Do Not Version

- Python caches: `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.pytest_tmp/`
- Local environments: `.venv/`, `venv/`, `.env`
- Generated ESG outputs under module `outputs/` folders
- Production-control runs under `ESGProductionControlCenter/runs/`
- Large corpora and downloaded PDFs: `ESGFinalCorpus/`, `data/dossier_ingestion_0/`

## Version

- Python source files
- Tests and test fixtures that are small and synthetic
- Contracts and schemas
- CLI scripts and project hygiene tools
- Documentation and validation-command reports
- Requirements files and pytest configuration

## First Commit Example

```powershell
git add .gitignore GIT_SETUP_GUIDE.md pytest.ini tools tests
git status --short
git commit -m "Add project hygiene tooling"
```

Review the full status before committing. Do not add generated outputs or PDFs.
