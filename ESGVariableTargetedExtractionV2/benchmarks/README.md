# Benchmarks

## schneider_tcfd_2023_manual_baseline_template.csv

Manual reading of Schneider Electric TCFD 2023 report (36 pages).
Used as ground truth for V1 vs V2 benchmark on a known document.

Columns:
- `page`: PDF page number
- `indicator`: human-readable indicator name
- `indicator_family`: target variable family
- `value`: extracted value
- `unit`: unit of measure
- `error_type`: V1 classification result
  - `true_positive`: V1 correctly found this
  - `missed_indicator`: V1 missed this
  - `wrong_family`: V1 found it but misclassified the family
  - `section_number_false_positive`: V1 extracted section number as value

## Using the baseline

```bash
python ESGVariableTargetedExtractionV2/scripts/benchmark_v1_vs_v2.py \
  --v1-pilot-root "EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_10docs_v2" \
  --v2-output-root "ESGVariableTargetedExtractionV2/outputs" \
  --manual-baseline "ESGVariableTargetedExtractionV2/benchmarks/schneider_tcfd_2023_manual_baseline_template.csv" \
  --output-dir "ESGVariableTargetedExtractionV2/outputs/benchmark_v1_vs_v2"
```
