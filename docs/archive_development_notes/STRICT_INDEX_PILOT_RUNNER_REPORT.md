# STRICT_INDEX_PILOT_RUNNER — Implementation Report

## Overview

`run_strict_index_pilot.py` is a **standalone CLI orchestrator** for the ESG extraction pipeline.
It reads a strict-filtered document index, validates every safety invariant, and either
performs a **dry-run** (default) or triggers the real pipeline steps sequentially
per document.

---

## Safety Invariants Enforced

| Rule | Where enforced |
|------|----------------|
| Index filename must be exactly `extraction_index_strict_likely_valid.csv` | `validate_args()` — `sys.exit(1)` on violation |
| `--execute` requires `--max-documents` | `validate_args()` |
| `--max-documents` cannot exceed 20 | `validate_args()` |
| Non-empty `output-root` rejected without `--overwrite` | `validate_args()` |
| Zero documents after filtering → abort | `main()` |
| `apply-review-and-build-dataset` requires `--decisions-root` | `validate_args()` |
| No Internet calls | Stdlib-only; no `requests`, `httpx`, etc. |
| No auto-accept (proposed_decision != "accept_candidate") | Code never assigns this string |
| All subprocesses use `sys.executable` | `run_step()` + assertion |
| All outputs written only under `<output-root>/` | All path construction anchored to `output_root` |

---

## Architecture

```
run_strict_index_pilot.py
├── build_parser()               # argparse CLI definition
├── validate_args()              # global safety checks → sys.exit(1) on violation
├── load_index()                 # CSV reader
├── filter_documents()           # slug / year / doc-type / file-exists / max-docs
├── CommandLog                   # append-only JSONL command log
├── run_step()                   # subprocess wrapper (dry-run aware)
│
├── step_01_information_extraction()
├── step_02_orchestrator()
├── step_03_indicator_validation()
├── step_04_build_review_workspace()
├── step_05_apply_review()
├── step_06_indicator_database()
├── step_08_variable_dataset()
│
├── build_top_review_candidates()   # produces top_review_candidates.csv
├── build_empty_decisions_file()    # smoke-test mode: empty decisions
│
├── process_document_prepare_review()
├── process_document_apply_review()
├── process_document_smoke_test()
│
└── main()                       # top-level orchestrator
```

---

## Modes

### `prepare-review` (default)

Steps per document: 1 → 2 → 3 → 4 → produce `top_review_candidates.csv`

Stops here. Does NOT apply decisions. Does NOT create `review_decisions_filled.csv`.

### `apply-review-and-build-dataset`

Requires human-filled decisions at:
`<decisions-root>/<slug>/<year>/<doc_type>/review_decisions_filled.csv`

If missing for a document → status `skipped_no_decisions`, pipeline continues.

Steps: 5 → 6 → copy to `_indicator_databases/` → 8 (variable dataset)

### `smoke-test-empty-review`

Generates empty decisions (proposed_decision="") for every candidate.
Never sets proposed_decision="accept_candidate".
Runs steps 5 → 6 → copy → 8 to prove pipeline robustness.

---

## Output Structure

```
<output-root>/
  pilot_run_summary.json        # machine-readable run summary
  pilot_run_report.md           # human-readable report
  pilot_command_log.jsonl       # one JSON line per command executed
  selected_documents.csv
  skipped_documents.csv
  failed_documents.csv

  <slug>/<year>/<doc_type>/<doc_id_safe>/
    01_information_extraction/
    02_orchestrator/
    03_validation/
    04_review_workspace/
    top_review_candidates.csv         # prepare-review output
    review_workspace_summary.json     # prepare-review summary
    05_review_applied/                # apply/smoke only
    06_indicator_database/            # apply/smoke only
    smoke_test_empty_decisions.csv    # smoke only
    logs/
      step_01_information_extraction.log
      step_02_orchestrator.log
      step_03_validation.log
      step_04_review_workspace.log
      step_05_apply_review.log
      step_06_indicator_database.log

  _indicator_databases/             # apply/smoke only
  _variable_dataset/                # apply/smoke only
```

---

## Stdlib-Only Implementation

Dependencies: `pathlib`, `subprocess`, `csv`, `json`, `shutil`, `argparse`,
`datetime`, `sys`, `logging`, `time`, `importlib`. No third-party packages.

---

## Test Suite

`tests/test_strict_index_pilot_runner_v10.py` — 12 synthetic-fixture tests:

| # | Test | What it checks |
|---|------|----------------|
| 1 | `test_pilot_runner_script_exists` | Script file exists |
| 2 | `test_refuses_non_strict_index` | Non-matching filename → SystemExit |
| 3 | `test_requires_max_documents_for_execute` | `--execute` without `--max-documents` → SystemExit |
| 4 | `test_refuses_too_many_documents` | `--max-documents=25` → SystemExit |
| 5 | `test_dry_run_default_no_subprocess` | Dry-run: no subprocess, summary produced |
| 6 | `test_loads_and_filters_by_company_slug` | Filter logic correctness |
| 7 | `test_skips_missing_files` | `final_file_exists=False` → excluded |
| 8 | `test_prepare_review_does_not_auto_accept` | Source code inspection: no accept_candidate |
| 9 | `test_top_review_candidates_generation` | Sorting: possible_indicator first |
| 10 | `test_apply_review_requires_decisions_root` | Missing `--decisions-root` → SystemExit |
| 11 | `test_summary_schema_keys` | All required JSON keys present |
| 12 | `test_subprocess_uses_sys_executable` | Source inspection: no hardcoded python/python3 |
