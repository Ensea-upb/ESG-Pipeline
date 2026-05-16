# ESGExtractionOrchestrator

Candidate-only full extraction orchestrator.

It runs:

- `ESGCSVExtraction`
- `ESGVisualExtraction`
- `ESGTableExtraction`

on an existing `ESGInformationExtraction` output folder and consolidates all candidates into a single CSV/JSONL.

It does not modify source outputs, PDFs, or any extraction module. It does not produce scores or validated ESG indicators.

## v1.1 - Cache and Audited Deduplication

`run_full_extraction.py` supports:

- `--reuse-existing`: reuse existing `csv/`, `visual/`, and `table/` sub-engine outputs when their required files already exist.
- `--force-rerun`: force the three sub-engines to run again.

The consolidated layer now keeps every candidate in `consolidated_candidates.csv/jsonl` and writes an audited canonical view in `consolidated_unique_candidates.csv/jsonl`. Duplicate groups are listed in `consolidated_duplicate_groups.csv/jsonl`; no candidate is silently deleted.
