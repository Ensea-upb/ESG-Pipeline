# V1 vs V2 Benchmark Guide

## Overview

This guide covers running a systematic comparison between V1 (ESGExtractionOrchestrator) and V2 (ESGVariableTargetedExtractionV2) on the 10 pilot documents, using the Schneider TCFD 2023 manual baseline as ground truth.

---

## Prerequisites

1. V1 pilot outputs exist at `EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_10docs_v2/`
2. V2 extraction has been run on the same 10 documents (see Step 2 below)
3. Manual baseline: `ESGVariableTargetedExtractionV2/benchmarks/schneider_tcfd_2023_manual_baseline_template.csv`

---

## Step 1: Run Unit Tests

```bash
cd C:\Users\hp\Desktop\ESG
python -m pytest ESGVariableTargetedExtractionV2/tests -q
```

Expected: all 89 tests pass. If any fail, do not proceed to benchmark — fix first.

---

## Step 2: Run V2 on All 10 Pilot Documents

Find all document input directories:

```bash
dir EXTERNAL_AUDIT_RUNS\strict_pilot_prepare_review_10docs_v2 /s /b | findstr "01_information_extraction"
```

For each document, run V2 extraction. Example for TotalEnergies 2024 URD:

```bash
python ESGVariableTargetedExtractionV2/scripts/build_targeted_extraction_v2.py ^
  --input-dir "EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_10docs_v2/totalenergies/2024/01_urd_annual_report/<doc_id>/01_information_extraction" ^
  --output-dir "ESGVariableTargetedExtractionV2/outputs/totalenergies_2024_urd" ^
  --embedding-backend lexical ^
  --overwrite
```

Repeat for each of the 10 documents, using the appropriate `--output-dir` per document.

---

## Step 3: Validate Each V2 Output

```bash
python ESGVariableTargetedExtractionV2/scripts/validate_targeted_extraction_v2.py ^
  --output-dir "ESGVariableTargetedExtractionV2/outputs/totalenergies_2024_urd" ^
  --contract-path "ESGVariableTargetedExtractionV2/contracts/targeted_candidates_v2_contract.json"
```

Expected per document: `status: ok` or `status: warning` (never `failed`).

---

## Step 4: Run the Benchmark

```bash
python ESGVariableTargetedExtractionV2/scripts/benchmark_v1_vs_v2.py ^
  --v1-pilot-root "EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_10docs_v2" ^
  --v2-output-root "ESGVariableTargetedExtractionV2/outputs" ^
  --manual-baseline "ESGVariableTargetedExtractionV2/benchmarks/schneider_tcfd_2023_manual_baseline_template.csv" ^
  --output-dir "ESGVariableTargetedExtractionV2/outputs/benchmark_v1_vs_v2"
```

---

## Benchmark Outputs

| File | Contents |
|------|----------|
| `v1_vs_v2_comparison_report.md` | Narrative comparison with tables |
| `v1_vs_v2_candidate_counts.csv` | Per-document candidate counts V1 vs V2 |
| `v1_vs_v2_variable_coverage.csv` | Per-variable coverage rate V1 vs V2 |
| `benchmark_summary.json` | Machine-readable aggregate metrics |

---

## Interpretation

### Candidate Counts

V1 pilot baseline: 6,027 candidates on 10 documents.
V2 is expected to produce **fewer** candidates with **higher precision**:

- V2 rejects ISO codes, section numbers, page numbers — these alone account for a significant share of V1 FPs
- V2 requires evidence (quote not empty) for every `candidate_found`
- V2 validates unit-variable coherence before accepting

A lower candidate count with a higher `candidate_found` rate is a positive signal.

### Variable Coverage

Check `v1_vs_v2_variable_coverage.csv`:
- V2 should have equal or higher coverage on environmental variables (well-documented in ESG reports)
- V2 may have lower coverage on financial variables (rarely in sustainability PDFs — expected)
- If V2 has 0% coverage on `co2_emissions` or `energy_consumption`, investigate retrieval

### Schneider TCFD 2023 Baseline

The manual baseline has 17 indicators with classified error types:

| Error Type | Count | V2 Target |
|------------|-------|-----------|
| `true_positive` | 10 | V2 should also find these |
| `wrong_family` | 3 | V2 variable mapping should fix these |
| `missed_indicator` | 1 | V2 recall should recover this |
| `section_number_false_positive` | 1 | V2 FP rejection should eliminate this |

For the section number FP: V1 extracted an ISO-standard section number as an energy investment value. V2's `_is_section_number()` pattern should reject this.

For the `wrong_family` cases: V1 misclassified e.g. avoided emissions as "boundary" family. V2's variable catalog has specific query terms that should route these to the correct variable.

### Success Criteria

| Metric | V1 Baseline | V2 Target |
|--------|-------------|-----------|
| Missing value rate | 52.3% | < 40% |
| ISO/section FP rate | ~15% of candidates | < 2% |
| Candidates in correct variable family | ~38% | > 55% |
| `candidate_found` with non-empty quote | ~60% | 100% (hard constraint) |
| Documents with 0 candidates for co2_emissions | unknown | 0 (all 10 docs have CO2 data) |

---

## Troubleshooting

### All candidates show `no_evidence_found`

The retrieval found no chunks above the min_relevance_score threshold. Check:
1. Does `document_chunks_v2.csv` have chunks? If empty, `input_dir` may be wrong.
2. Is the lexical backend fitting on enough text? The document may be very short.
3. Lower `--top-k` threshold or check if text_blocks.jsonl is non-empty in the input dir.

### High `unit_mismatch` rate

The variable catalog may have incomplete `expected_units`. Check `config/variable_semantic_catalog_v1.yaml` for the affected variable and add the missing unit pattern.

### `fp_rejected` for real values

The FP rejection patterns may be too aggressive. Check `constrained_extractor.py`:
- `_is_iso_standard_value()`: only triggers for bare 5-digit integers without context
- `_is_section_number()`: only triggers for `\d{1,2}\.\d{1,2}(\.\d+)?` pattern

If a real value like "14.1 MtCO2e" is being rejected, the section number regex needs tightening to require no trailing unit.

### Benchmark script finds no V2 outputs

The benchmark looks for `targeted_candidates_v2.csv` in subdirectories of `--v2-output-root`. Ensure each V2 run wrote to a distinct subdirectory:
```
ESGVariableTargetedExtractionV2/outputs/
  totalenergies_2024_urd/
    targeted_candidates_v2.csv   ← found
  schneider_2023_tcfd/
    targeted_candidates_v2.csv   ← found
  ...
```

---

## Quick Single-Doc Smoke Test

To validate V2 works before running all 10 documents:

```bash
python ESGVariableTargetedExtractionV2/scripts/build_targeted_extraction_v2.py ^
  --input-dir "EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_10docs_v2/totalenergies/2024/01_urd_annual_report/<doc_id>/01_information_extraction" ^
  --output-dir "ESGVariableTargetedExtractionV2/outputs/smoke_test" ^
  --embedding-backend lexical ^
  --variables water_consumption,human_capital,co2_emissions,energy_consumption,diversity ^
  --overwrite
```

Smoke test passes if:
- `targeted_candidates_v2.csv` is non-empty
- At least one `candidate_found` candidate has a non-empty `quote`
- No crash, even if HF model unavailable
- `EXTERNAL_AUDIT_RUNS/` directory mtime unchanged after run
