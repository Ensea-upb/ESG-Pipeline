# STRICT_INDEX_PILOT_RUNNER — Validation Commands

All commands assume the working directory is `C:\Users\hp\Desktop\ESG\`.

---

## 1. Run the dedicated test suite (12 tests)

```powershell
python -m pytest "C:\Users\hp\Desktop\ESG\tests\test_strict_index_pilot_runner_v10.py" -v
```

Expected: **12 passed**.

---

## 2. Run global project regression suite (no business module regressions)

```powershell
python -m pytest "C:\Users\hp\Desktop\ESG" `
    --ignore="C:\Users\hp\Desktop\ESG\ESGOrchestrator" `
    -q --tb=no -x
```

Expected: 0 failures, 0 errors (existing suite unaffected).

---

## 3. Dry-run smoke test (default mode — no subprocesses launched)

```powershell
python "C:\Users\hp\Desktop\ESG\run_strict_index_pilot.py" `
    --index-path "C:\Users\hp\Desktop\ESG\DocumentPostProcessing\data\quality_audit_v2\extraction_index_strict_likely_valid.csv" `
    --output-root "C:\Users\hp\Desktop\ESG\PILOT_DRY_RUN_TEST" `
    --max-documents 3
```

Verify outputs:
```powershell
Get-Content "C:\Users\hp\Desktop\ESG\PILOT_DRY_RUN_TEST\pilot_run_summary.json"
```

Expected assertions in the JSON:
- `"dry_run": true`
- `"execute": false`
- `"documents_processed": 0`
- `"documents_selected": 3`
- `per_document` has 3 entries with `"status": "dry_run_selected"`

---

## 4. Dry-run with company slug filter

```powershell
python "C:\Users\hp\Desktop\ESG\run_strict_index_pilot.py" `
    --index-path "C:\Users\hp\Desktop\ESG\DocumentPostProcessing\data\quality_audit_v2\extraction_index_strict_likely_valid.csv" `
    --output-root "C:\Users\hp\Desktop\ESG\PILOT_DRY_TOTALENERGIES" `
    --max-documents 6 `
    --company-slug totalenergies
```

Expected: `"documents_selected": 6` (TotalEnergies has 6 docs in the index).

---

## 5. Safety check — wrong index filename

```powershell
python "C:\Users\hp\Desktop\ESG\run_strict_index_pilot.py" `
    --index-path "C:\Users\hp\Desktop\ESG\DocumentPostProcessing\data\quality_audit_v2\extraction_index_large.csv" `
    --output-root "C:\Users\hp\Desktop\ESG\PILOT_REFUSED" `
    --max-documents 5
```

Expected: script exits with code 1 and prints `"Refused: index filename must be exactly..."`.

---

## 6. Safety check — execute without max-documents

```powershell
python "C:\Users\hp\Desktop\ESG\run_strict_index_pilot.py" `
    --index-path "C:\Users\hp\Desktop\ESG\DocumentPostProcessing\data\quality_audit_v2\extraction_index_strict_likely_valid.csv" `
    --output-root "C:\Users\hp\Desktop\ESG\PILOT_REFUSED2" `
    --execute
```

Expected: exits with code 1, `"--execute requires --max-documents"`.

---

## 7. Safety check — max-documents > 20

```powershell
python "C:\Users\hp\Desktop\ESG\run_strict_index_pilot.py" `
    --index-path "C:\Users\hp\Desktop\ESG\DocumentPostProcessing\data\quality_audit_v2\extraction_index_strict_likely_valid.csv" `
    --output-root "C:\Users\hp\Desktop\ESG\PILOT_REFUSED3" `
    --max-documents 25
```

Expected: exits with code 1, `"exceeds hard limit of 20"`.

---

## 8. Safety check — apply-review without decisions-root

```powershell
python "C:\Users\hp\Desktop\ESG\run_strict_index_pilot.py" `
    --index-path "C:\Users\hp\Desktop\ESG\DocumentPostProcessing\data\quality_audit_v2\extraction_index_strict_likely_valid.csv" `
    --output-root "C:\Users\hp\Desktop\ESG\PILOT_REFUSED4" `
    --max-documents 5 `
    --mode apply-review-and-build-dataset
```

Expected: exits with code 1, `"requires --decisions-root"`.

---

## 9. Real execution — prepare-review (3 documents)

**WARNING: runs the actual ESG pipeline. Requires all business modules to be functional.**

```powershell
python "C:\Users\hp\Desktop\ESG\run_strict_index_pilot.py" `
    --index-path "C:\Users\hp\Desktop\ESG\DocumentPostProcessing\data\quality_audit_v2\extraction_index_strict_likely_valid.csv" `
    --output-root "C:\Users\hp\Desktop\ESG\PILOT_REAL_PREPARE" `
    --max-documents 3 `
    --execute
```

Expected:
- `pilot_run_summary.json`: `"execute": true`, `"dry_run": false`
- Per document: `status` is either `"success"` or `"failed"`
- `top_review_candidates.csv` produced in each successful doc dir
- `review_workspace_summary.json` produced in each successful doc dir

---

## 10. Real execution — smoke-test-empty-review (3 documents)

**Requires prepare-review to have succeeded first (step 4 workspace must exist).**

```powershell
python "C:\Users\hp\Desktop\ESG\run_strict_index_pilot.py" `
    --index-path "C:\Users\hp\Desktop\ESG\DocumentPostProcessing\data\quality_audit_v2\extraction_index_strict_likely_valid.csv" `
    --output-root "C:\Users\hp\Desktop\ESG\PILOT_REAL_PREPARE" `
    --max-documents 3 `
    --mode smoke-test-empty-review `
    --overwrite `
    --execute
```

Expected:
- `_indicator_databases/` populated
- `_variable_dataset/` populated
- `pilot_run_summary.json`: `"variable_dataset_produced": true`

---

## GO / NO-GO Decision Criteria

| Criterion | Check |
|-----------|-------|
| 12/12 runner tests pass | `pytest tests/test_strict_index_pilot_runner_v10.py -v` → 12 passed |
| Global pytest: 0 regressions | `pytest --ignore=ESGOrchestrator -q --tb=no -x` → 0 failures |
| Dry-run summary correct | `pilot_run_summary.json` has `dry_run=true`, `documents_processed=0` |
| No auto-accept in code | Test 8 passes (source inspection) |
| Non-strict index rejected | Test 2 passes |
| max-documents enforced in execute mode | Test 3 passes |
