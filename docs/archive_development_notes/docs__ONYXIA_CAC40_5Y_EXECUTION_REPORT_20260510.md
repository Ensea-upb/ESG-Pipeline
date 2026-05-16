# Onyxia CAC40 5Y Execution Report

Run id: `onyxia_cac40_5y_full_20260510_085527`

Run directory:
`ESGOrchestrator/runs/onyxia_cac40_5y_full_20260510_085527/`

## Result

- Total tasks: 4400
- Success: 3382
- Skipped not applicable: 1000
- Failed: 18

The skipped tasks mainly correspond to document types without configured
retrievers. They are not treated as pipeline failures.

## Disk Incident

Onyxia hit `OSError: [Errno 28] No space left on device` on
`/home/onyxia/work`.

Cause: physical PDF duplication across intermediate corpus directories:

- `data/dossier_ingestion_0`
- `ESGCorpus`
- `ESGCorpusTaxonomy`
- `ESGFinalCorpus`

After deleting heavy pilot runs and rerunning post-processing with the same
run id, `final_summary.json`, `coverage_matrix.csv`, validation, selection,
and `ESGFinalCorpus` were finalized.

## Post-Processing Counts

- Manifests found: 6675
- Documents loaded: 6217
- Registry errors: 0
- Unique SHA-256 documents: 3873
- Exact duplicate groups: 1133
- Documents planned by family: 4321
- Files present/copied: 4261
- Missing source files: 60
- Technically valid PDFs: 4259
- Unreadable PDFs: 2
- Selected documents: 1147
- Rejected documents: 3174

## Quality Audit V2

- Raw selected documents: 1147
- `KEEP_LIKELY_VALID`: 552
- `REVIEW_STANDARD`: 434
- `REVIEW_HIGH_PRIORITY_COMPANY_NOT_DETECTED`: 96
- `QUARANTINE_LIKELY_WRONG_COMPANY`: 65

Operational corpus:

- Strict corpus: 552 documents
- Usable excluding quarantine: 1082 documents
- Quarantine exclusion list: 65 documents

## Authoritative Indexes

Do not use raw `ESGFinalCorpus` directly for ESG extraction.

Strict index for first extraction tests:

`ESGOrchestrator/runs/onyxia_cac40_5y_full_20260510_085527/postprocessing/quality_audit_v2/extraction_index_strict_likely_valid.csv`

Large safe index:

`ESGOrchestrator/runs/onyxia_cac40_5y_full_20260510_085527/postprocessing/quality_audit_v2/extraction_index_usable_excluding_quarantine.csv`

Exclusion index:

`ESGOrchestrator/runs/onyxia_cac40_5y_full_20260510_085527/postprocessing/quality_audit_v2/exclusion_index_quarantine_wrong_company.csv`

## Recommended Next Step

Start ESG extraction on 10 to 20 documents from the strict index only. Preserve
`company_name`, `fiscal_year`, `official_doc_type`, `final_path`,
`page_number`, `text_snippet`, and `extraction_method` for every extracted
evidence record.
