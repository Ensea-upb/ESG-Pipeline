# Output Contract V1

Version: `1.0.0`

This contract freezes the documentary PDF engine outputs. It is not an ESG extraction contract: no ESG metric, indicator, score, RAG index, vector database, OCR output, graph interpretation, or table-value interpretation is produced.

## Global Invariants

- Every JSON object has `schema_version`.
- `document_id` is stable across all files for one extraction.
- JSONL files contain one valid JSON object per line.
- `page_number` starts at 1.
- `evidence_id` values are unique.
- Every evidence in `evidence_store.jsonl` appears in `multimodal_evidence_index.jsonl`.
- Quarantined evidence is never `eligible_for_future_extraction`.
- `review_required=true` evidence is never `eligible_for_future_extraction`.
- Table evidences reference an existing `table_id`.
- Figure evidences reference an existing `figure_id`.
- Non-null `section_id` references exist in `section_index.jsonl`.
- The engine writes only to `--output-dir` and never modifies source PDFs or `ESGFinalCorpus`.

## File Contracts

### document_record.json

Role: immutable technical identity of the source PDF.
Granularity: one object per PDF.
Required fields: `schema_version`, `document_id`, `sha256`, `document_path`, `file_name`, `page_count`, `loading_status`, `created_at`.
Allowed status: `loading_status` is typically `readable` or `failed`.
Links: `document_id` anchors all other files.

Example:

```json
{"schema_version":"1.0.0","document_id":"doc1","sha256":"...","document_path":".../document.pdf","file_name":"document.pdf","page_count":20,"loading_status":"readable","created_at":"2026-05-10T00:00:00+00:00"}
```

### page_index.jsonl

Role: page-level extraction index.
Granularity: one line per processed page.
Required fields: `schema_version`, `page_id`, `document_id`, `page_number`, `width`, `height`, `rotation`, `extraction_status`, `text_char_count`, `has_text`.
Invariant: `page_number >= 1`, `page_id` unique.

### text_blocks.jsonl

Role: raw and classified text blocks.
Granularity: one line per extracted text block.
Required fields: `schema_version`, `text_block_id`, `document_id`, `page_id`, `page_number`, `block_type`, `text`, `bbox`, `reading_order`.
Common block types: `header`, `footer`, `caption`, `list_item`, `toc_entry`, `footnote`, `title`, `paragraph`, `unknown`.
Links: `text_block_id` is referenced by sections and evidences.

### section_candidates.jsonl

Role: audit trail of accepted and rejected heading candidates.
Granularity: one line per candidate.
Required fields: `schema_version`, `candidate_id`, `document_id`, `text_block_id`, `page_number`, `text`, `candidate_status`, `block_type`, `confidence`.
Invariant: rejected candidates remain auditable and are not deleted.

### section_index.jsonl

Role: conservative section index.
Granularity: one line per accepted section.
Required fields: `schema_version`, `section_id`, `document_id`, `section_title`, `section_type`, `page_start`, `page_end`, `start_element_id`, `source_heading_block_id`, `section_quality_score`, `is_suspicious_section`, `suspicion_reasons`, `evidence_policy`.
Allowed `evidence_policy`: `normal`, `review_required`, `quarantine`.
Invariant: `page_start <= page_end`.

### suspicious_sections.jsonl

Role: retained audit list of suspicious sections.
Granularity: one line per suspicious section.
Required fields: `schema_version`, `document_id`, `section_id`, `section_title`, `section_quality_score`, `evidence_policy`, `suspicion_reasons`, `evidence_count`, `sample_evidence_quotes`.
Invariant: suspicious sections are retained, not removed.

### evidence_store.jsonl

Role: localized documentary evidences.
Granularity: one line per evidence.
Required fields: `schema_version`, `evidence_id`, `document_id`, `page_id`, `page_number`, `evidence_type`, `quote`, `bbox`, `section_id`, `source_element_type`, `source_element_id`, `evidence_policy`, `review_required`, `is_quarantined_evidence`.
Allowed `evidence_type`: `section_heading`, `paragraph`, `table`, `figure`, `list_item`, `footnote`, `caption`, `unknown`.
Invariant: evidence is documentary only; it is not an ESG metric.

### table_index.jsonl

Role: detected table objects.
Granularity: one line per table or table-like candidate.
Required fields: `schema_version`, `table_id`, `document_id`, `page_id`, `page_number`, `section_id`, `extraction_status`, `row_count`, `column_count`, `cell_count`, `table_confidence`, `review_required`, `is_quarantined_table`, `table_quality_flags`.
Allowed `extraction_status`: `parsed`, `detected_not_parsed`, `low_confidence`, `empty_table`, `failed`.
Invariant: ambiguous tables are kept with explicit status.

### table_cells.jsonl

Role: raw table cell structure.
Granularity: one line per cell.
Required fields: `schema_version`, `cell_id`, `table_id`, `document_id`, `page_id`, `page_number`, `row_index`, `column_index`, `text`, `bbox`, `is_header_cell`, `cell_confidence`, `normalized_text`.
Invariant: row and column indexes start at 0. Cell text is not interpreted as ESG.

### figure_index.jsonl

Role: detected figure or visual objects.
Granularity: one line per figure/visual candidate.
Required fields: `schema_version`, `figure_id`, `document_id`, `page_id`, `page_number`, `section_id`, `figure_type`, `extraction_status`, `figure_confidence`, `review_required`, `is_quarantined_figure`, `figure_quality_flags`.
Allowed status: `detected`, `low_confidence`, `detected_not_interpreted`, `failed`.
Invariant: graph values are never read.

### multimodal_evidence_index.jsonl

Role: normalized cross-modality evidence index.
Granularity: one line per evidence from `evidence_store.jsonl`.
Required fields: `schema_version`, `multimodal_evidence_id`, `evidence_id`, `document_id`, `evidence_type`, `source_modality`, `source_element_type`, `source_element_id`, `evidence_policy`, `review_required`, `is_quarantined_evidence`, `downstream_use_policy`.
Allowed `source_modality`: `text`, `table`, `figure`.
Allowed `downstream_use_policy`: `eligible_for_future_extraction`, `review_before_extraction`, `exclude_from_automatic_extraction`.

### document_inventory.json

Role: document-level inventory summary.
Granularity: one object per PDF.
Required fields: `schema_version`, `document_id`, `pdf_path`, `page_count`, `pages_processed`, `text_blocks_count`, `sections_count`, `evidence_count`, `extraction_readiness_status`, `generated_at`.
Allowed readiness: `ready_for_experimental_extraction`, `partially_ready`, `not_ready`.

### multimodal_statistics.json

Role: multimodal evidence counters and samples.
Required fields: `schema_version`, `document_id`, `total_multimodal_evidences`, `evidence_by_modality`, `downstream_use_policy_distribution`.
Invariant: total equals the number of rows in `multimodal_evidence_index.jsonl`.

### consistency_report.json

Role: machine-readable cross-file audit report.
Required fields: `schema_version`, `document_id`, `generated_at`, `overall_status`, `errors_count`, `warnings_count`, `checks_count`, `findings`.
Allowed `overall_status`: `pass`, `warning`, `fail`.

### audit_findings.jsonl

Role: detailed audit findings.
Required fields: `schema_version`, `finding_id`, `document_id`, `severity`, `category`, `check_name`, `status`, `message`, `related_file`, `recommendation`.
Allowed severity: `info`, `minor`, `major`, `critical`.

### quality_report.jsonl

Role: technical quality checks generated during extraction.
Required fields: `schema_version`, `quality_check_id`, `target_type`, `target_id`, `check_name`, `status`, `severity`, `message`, `created_at`.
Allowed status: `pass`, `warning`, `fail`, `info`.

### extraction_summary.json

Role: final run summary and counters.
Required fields: `schema_version`, `engine_contract_version`, `document_id`, `status`, `pages_processed`, `text_blocks_count`, `evidence_count`, `errors_count`, `warnings_count`.
Invariant: `engine_contract_version` must be `1.0.0`.
