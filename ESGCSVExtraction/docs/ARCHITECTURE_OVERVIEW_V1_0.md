# ESGCSVExtraction v1.0 - Architecture Overview

## Position in the ESG Project

`ESGCSVExtraction` is a separate layer after `ESGInformationExtraction`.

```text
ESGInformationExtraction outputs
  -> multimodal documentary evidence
  -> ESGCSVExtraction candidate rules
  -> global and typed CSV candidates
  -> candidate audit and contract validation
```

## Separation of Responsibilities

- `ESGInformationExtraction`: reads PDFs and creates documentary structures, evidence, multimodal indexes, and audit reports.
- `ESGCSVExtraction`: reads existing documentary outputs and creates CSV candidates only.
- Future ESG layer: may validate indicators, reconcile units, compare years, and decide whether a candidate becomes usable data.

## Main Components

- `scripts/run_csv_extraction.py`: one-output CSV candidate extraction CLI.
- `scripts/run_multi_document_audit.py`: batch audit over multiple documentary outputs.
- `scripts/validate_csv_outputs.py`: CSV contract validator.
- `src/esg_csv_extraction/extractor.py`: rule-based candidate extraction and typed CSV export.
- `src/esg_csv_extraction/multi_document_audit.py`: batch orchestration and aggregation.
- `src/esg_csv_extraction/validators.py`: output contract validation.
- `contracts/csv_output_contract_v0.json`: machine-readable CSV contract.

## Outputs

The engine keeps one global CSV plus typed CSVs. All rows preserve traceability:

- `document_id`
- `evidence_id`
- `page_number`
- `section_id`
- `quote`
- `confidence`

## Why ESG Extraction Must Stay Separate

The CSV layer does not know whether a value is correct, complete, comparable, or regulatory-grade. It only surfaces candidates for review. A future ESG extraction module must separately handle validation, unit harmonization, period logic, duplicate resolution, and reporting requirements.
