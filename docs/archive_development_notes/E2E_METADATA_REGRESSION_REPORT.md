# E2E Metadata Regression Report — MetadataPropagationFix v1.0
## TotalEnergies 2024 — Full Pipeline Validation

**Date:** 2026-05-14  
**Severity (original bug):** Critical — produced 0 found ESG values despite correct data  
**Decision:** ✅ GO — StrictIndexPilotRunner v1.0

---

## 1. Bug Reproduced (Pre-Fix Reference Run)

### Symptom
- `ESGIndicatorDatabase` produced 2 correct extraction rows: `human_capital = 102,887 employees` and `water_consumption = 92 Mm3`
- `company` field was **empty** in `indicator_preparation_database.csv`
- `fiscal_year` on water_consumption row was **"2015"** (overwritten by `year_raw`) instead of "2024"
- `ESGVariableDatasetBuilder` produced **0 found values**

### Root Cause Chain

```
run_pdf_extraction.py
  → no --company/--fiscal-year CLI args
  → document_record.json: company="" fiscal_year=""

ESGVisualExtraction (loader.py)
  → visual_candidates.csv: no company/fiscal_year columns at all
  → company and fiscal_year absent from all visual candidates

ESGExtractionOrchestrator (candidate_consolidator.py)
  → company/fiscal_year not in CONSOLIDATED_FIELDS
  → consolidated_candidates.csv: company="" fiscal_year=""

ESGIndicatorValidation, ESGManualReview
  → pass through empty company/fiscal_year unchanged (no warning)

ESGIndicatorDatabase
  → indicator_preparation_database.csv: company="" fiscal_year="2015"
  → no warnings emitted on missing company/fiscal_year

ESGVariableDatasetBuilder (value_selector.py)
  → select_values() groups by (company, year) tuples from CLI
  → ("", "") not in company_years → 0 rows matched
  → 0 found values produced
```

---

## 2. Fixes Applied (MetadataPropagationFix v1.0)

| Module | Fix |
|--------|-----|
| `ESGInformationExtraction/run_pdf_extraction.py` | Added 9 optional CLI args: `--company`, `--company-name`, `--company-slug`, `--fiscal-year`, `--official-doc-type`, `--document-family`, `--final-path`, `--source-index-path`, `--corpus-run-id`. Injected additively into `document_record.json`, `document_inventory.json`, `evidence_store.jsonl`, `multimodal_evidence_index.jsonl`. |
| `ESGVisualExtraction/src/esg_visual_extraction/loader.py` | Added `_resolve_company_year()` using authority-order fallback: `document_record.json` → `document_inventory.json` → path pattern inference. Added `company`/`fiscal_year` to `CANDIDATE_FIELDS` and `visual_candidates.csv`. |
| `ESGExtractionOrchestrator/src/esg_extraction_orchestrator/candidate_consolidator.py` | Added `company`/`fiscal_year` to `CONSOLIDATED_FIELDS`. Added cross-row backfill: after collecting all rows, fills empty `company`/`fiscal_year` from rows sharing the same `document_id`. |
| `ESGIndicatorDatabase` | Added metadata-missing warnings to logger and summary JSON. |
| `ESGVariableDatasetBuilder/src/esg_variable_dataset_builder/dataset_builder.py` | Added `override_empty_company_from_cli` / `override_empty_year_from_cli` flags with early safety check. Added `metadata_missing_company_count` / `metadata_missing_fiscal_year_count` to summary. Fixed override check to fire **before** loading loop (catches multi-source case immediately). |

---

## 3. E2E Production Run — Post-Fix Results

**Document:** TotalEnergies 2024 URD (680 pages, 16.4 MB)  
**Pages extracted:** 30 (speed-limited test)  
**Output root:** `E2E_TEST_METADATA_FIX/`

### Step 1 — ESGInformationExtraction

`document_record.json`:
```json
{
  "schema_version": "1.0.0",
  "document_id": "totalenergies_2024_urd_e2e_metadata_fix",
  "company": "TotalEnergies",
  "company_name": "TotalEnergies SE",
  "fiscal_year": "2024",
  "official_doc_type": "URD",
  "loading_status": "readable",
  "page_count": 680
}
```
✅ `company` and `fiscal_year` now injected from CLI and written to all outputs.

### Step 2 — ESGExtractionOrchestrator

- Candidates consolidated: **335**
- Candidates with `company` field filled: **335 / 335** ✅
- Candidates with `fiscal_year` field filled: **335 / 335** ✅

### Steps 3–5 — Validation, Manual Review, Decisions

- 335 validation records produced, all with `company`/`fiscal_year`
- Manual review workspace: 335 items, 335 / 335 with `company` ✅
- 2 decisions accepted: `human_capital` (prep_001) + `water_consumption` (prep_002)

### Step 6 — ESGIndicatorDatabase

`indicator_preparation_database.csv` — final 2 rows:

| indicator_key | company | fiscal_year | year_raw | value_prepared | unit_prepared |
|---|---|---|---|---|---|
| `human_capital` | `totalenergies` | `2024` | `2024` | `102887` | `employees` |
| `water_consumption` | `totalenergies` | `2024` | `2015` | `92` | `Mm3` |

✅ `company` filled on both rows  
✅ `fiscal_year = 2024` on both rows  
✅ `year_raw = 2015` preserved for water_consumption but **did NOT overwrite** `fiscal_year`

### Step 7 — ESGVariableDatasetBuilder

`esg_variables_dataset_summary.json`:
```json
{
  "company_year_rows_count": 1,
  "variables_count": 31,
  "selected_rows_count": 31,
  "ignored_records_count": 0,
  "metadata_missing_company_count": 0,
  "metadata_missing_fiscal_year_count": 0,
  "quality": {
    "found_values_count": 2,
    "missing_values_count": 29,
    "status_counts": {
      "found": 2,
      "missing_from_corpus": 29
    }
  }
}
```

✅ `found_values_count = 2` (was **0** before fix)  
✅ `metadata_missing_company_count = 0`  
✅ `metadata_missing_fiscal_year_count = 0`  
✅ No manual patch required

---

## 4. Critical Rule Verified

> **`fiscal_year` (reporting year) is NEVER overwritten by `year_raw` (comparison year found in a quote).**

Water consumption row had `year_raw = 2015` (from quote: "compared to 2015 baseline") but `fiscal_year` correctly remained `2024`.  
This is tested in `test_fiscal_year_stays_2024_despite_year_raw_2015`.

---

## 5. Test Suite

**57 new tests** created across 9 test files:

| File | Tests | Status |
|------|-------|--------|
| `tests/test_metadata_propagation_audit_v01.py` | 6 | ✅ PASS |
| `ESGInformationExtraction/tests/test_metadata_propagation_v03.py` | 7 | ✅ PASS |
| `ESGVisualExtraction/tests/test_metadata_propagation_v04_visual.py` | 7 | ✅ PASS |
| `ESGExtractionOrchestrator/tests/test_metadata_propagation_v04_orchestrator.py` | 6 | ✅ PASS |
| `ESGIndicatorValidation/tests/test_metadata_propagation_v05_validation.py` | 5 | ✅ PASS |
| `ESGManualReview/tests/test_metadata_propagation_v05_review.py` | 3 | ✅ PASS |
| `ESGIndicatorDatabase/tests/test_metadata_propagation_v06_database.py` | 6 | ✅ PASS |
| `ESGVariableDatasetBuilder/tests/test_metadata_propagation_v07_builder.py` | 8 | ✅ PASS |
| `tests/test_e2e_metadata_regression_v08.py` | 9 | ✅ PASS |

**Full suite result:** `463 passed, 0 failed`  
_(includes 1 post-implementation fix to `test_override_flags_raise_error_without_single_document_mode` — early check moved before loading loop in `dataset_builder.py`)_

---

## 6. GO Decision

All criteria met:

- [x] `company` and `fiscal_year` propagated end-to-end without manual patch
- [x] `fiscal_year` never overwritten by `year_raw`
- [x] `found_values_count` went from **0 → 2** on identical source PDF
- [x] `metadata_missing_company_count = 0`, `metadata_missing_fiscal_year_count = 0`
- [x] All 463 tests pass
- [x] No score produced, no external sources used

**✅ GO — StrictIndexPilotRunner v1.0 can now be built.**

StrictIndexPilotRunner will:
1. Read `extraction_index_strict_likely_valid.csv`
2. Filter by company / year / doc_type
3. Select N documents maximum (configurable cap)
4. Transmit `company`, `fiscal_year`, `official_doc_type`, `final_path`, `corpus_run_id` to `run_pdf_extraction.py` via the new CLI args added in MetadataPropagationFix v0.3
5. Run the full pipeline sequentially for each document
6. Aggregate outputs into a multi-company ESG variable dataset
