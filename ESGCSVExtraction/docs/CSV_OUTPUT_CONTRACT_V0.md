# CSV Output Contract v0

This contract freezes the candidate CSV surface used by `ESGCSVExtraction` before any future ESG validation layer.

## Scope

The CSV engine consumes existing documentary outputs from `ESGInformationExtraction` and writes only candidate rows. It does not validate ESG indicators, produce scores, run OCR, use a vector database, or call an LLM.

## Required Files

- `esg_information_candidates.csv`
- `esg_information_candidates.jsonl`
- `observed_metrics.csv`
- `targets.csv`
- `policies.csv`
- `risks.csv`
- `boundary_contexts.csv`
- `methodology_contexts.csv`
- `visual_evidences.csv`
- `extraction_audit.csv`
- `candidate_audit_summary.json`
- `candidate_audit_findings.jsonl`
- `candidate_audit_samples.csv`
- `extraction_summary.json`

## Core Columns

Every global and typed CSV must contain:

- `document_id`
- `company`
- `fiscal_year`
- `information_type`
- `esg_category`
- `label`
- `raw_value`
- `raw_unit`
- `year`
- `source_modality`
- `page_number`
- `section_id`
- `evidence_id`
- `quote`
- `confidence`
- `review_required`
- `extraction_status`

## Allowed Information Types

- `observed_metric`
- `target`
- `policy_or_commitment`
- `risk_statement`
- `boundary_context`
- `methodology_context`
- `visual_evidence`

## Invariants

- `review_required` is always `True`.
- `extraction_status` is always `candidate_only`.
- `confidence` is never greater than `0.6`.
- No CSV may contain a `score` column or a `validated_metric` column.
- The sum of typed CSV rows must equal the global candidate CSV row count.
- Typed CSVs must contain only their matching `information_type`.

## Validation

```powershell
python ESGCSVExtraction/scripts/validate_csv_outputs.py `
  --output-dir "ESGCSVExtraction/outputs/lvmh_v10_csv_test" `
  --contract-path "ESGCSVExtraction/contracts/csv_output_contract_v0.json"
```
