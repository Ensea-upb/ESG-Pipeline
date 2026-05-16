# Metadata Propagation Contract — v1.0

## Purpose

This document defines the metadata contract for the ESG pipeline. All modules
must propagate the 12 metadata fields listed below without loss, modification,
or invention.

---

## 1. The 12 Metadata Fields

| Field | Type | Definition |
|---|---|---|
| `document_id` | string | Unique identifier for the PDF document within the corpus. Set once at extraction time. Never modified downstream. |
| `company` | string | Legal or common name of the reporting company (e.g., `TotalEnergies`, `LVMH`). Set from CLI or document_record.json. Never guessed from directory names. |
| `fiscal_year` | string | The reporting year declared in the document (e.g., `2024`). This is company-level metadata. NOT the year of a data point inside the document. |
| `official_doc_type` | string | The official document type classification (e.g., `URD`, `Sustainability Report`, `CDP Response`). |
| `final_path` | string | The canonical path of the PDF within ESGFinalCorpus, if applicable. |
| `source_engine` | string | The extraction engine that produced a candidate (`csv`, `table`, `visual`). |
| `information_type` | string | The type of evidence record (e.g., `esg_metric_candidate`, `visual_metric_candidate`). |
| `indicator_key` | string | The canonical indicator identifier (e.g., `human_capital`, `water_consumption`). |
| `value_prepared` | string | The cleaned numeric or qualitative value extracted from the document. |
| `unit_prepared` | string | The cleaned unit of measurement. |
| `year_raw` | string | The year referenced inside a quote or data cell (e.g., the year a number was measured). This is CONTENT metadata, not document metadata. |
| `year_prepared` | string | The cleaned year extracted from content. May differ from `fiscal_year`. |

---

## 2. Authority Order (5 Levels)

When a field value is available from multiple sources, the highest-authority source wins.
Lower-authority sources are only used when higher-authority sources provide no value.

| Priority | Source | Notes |
|---|---|---|
| 1 (highest) | CLI explicit argument | `--company`, `--fiscal-year` passed to the script |
| 2 | `document_record.json` | Written by ESGInformationExtraction; authoritative for document identity |
| 3 | `document_inventory.json` | Written by ESGInformationExtraction; secondary document metadata |
| 4 | `evidence_store.jsonl` / `multimodal_evidence_index.jsonl` | Evidence-level metadata; lower than document-level |
| 5 (lowest) | PDF content | Never used for `company` or `fiscal_year` |

---

## 3. `fiscal_year` vs `year_raw` — Critical Distinction

### Definition

- `fiscal_year` is **company-level metadata**: it is the year the company is *reporting for*.
  It is set once, at the document level, and never changes based on content.

- `year_raw` is **content metadata**: it is the year referenced inside a specific quote or data cell.

### Example

Document: TotalEnergies URD 2024

Quote: `"Fresh water withdrawal: 92 Mm3 in 2024 (compared to 85 Mm3 in 2015)"`

| Field | Value | Explanation |
|---|---|---|
| `fiscal_year` | `2024` | The company is reporting for fiscal year 2024 |
| `year_raw` | `2015` | A comparison year mentioned inside the quote |
| `year_prepared` | `2024` | The cleaned primary year from content context |

### Rule

> **NEVER overwrite `fiscal_year` with `year_raw` or `year_prepared`.**

`fiscal_year` is set from CLI arguments or `document_record.json` and must never be modified by any downstream module.

---

## 4. Rules for Missing Metadata

| Situation | Action |
|---|---|
| `company` is empty | Log warning `metadata_missing_company`. Do NOT invent a value. Do NOT silently proceed. |
| `fiscal_year` is empty | Log warning `metadata_missing_fiscal_year`. Do NOT infer from content. |
| `document_id` is empty | Log error. Record must be flagged for review. |
| `official_doc_type` is empty | Log info. Optional field; acceptable to be empty. |
| `final_path` is empty | Log info. Optional field; acceptable to be empty. |

Missing metadata is a **warning**, not a pipeline failure. The pipeline continues but flags the record.

---

## 5. Rules for Contradicting Metadata

| Situation | Action |
|---|---|
| CLI arg conflicts with `document_record.json` | CLI arg wins (priority 1). Log info. |
| `document_record.json` conflicts with `document_inventory.json` | `document_record.json` wins (priority 2). Log info. |
| Two source engines have different `company` for same `document_id` | Keep the value from highest-priority source. Log warning `metadata_company_conflict`. |
| `fiscal_year` from doc differs from `year_raw` in content | Both are preserved in their respective fields. Never merge. |

---

## 6. Module Responsibilities

| Module | Responsibility |
|---|---|
| `ESGInformationExtraction` | Set `document_id`, `company`, `fiscal_year`, `official_doc_type`, `final_path` in `document_record.json` and `document_inventory.json`. Propagate to evidence records if CLI args provided. |
| `ESGCSVExtraction` | Read `company`/`fiscal_year` from `document_record.json` or infer from corpus path. Write to candidates. |
| `ESGTableExtraction` | Same as ESGCSVExtraction. |
| `ESGVisualExtraction` | Read `company`/`fiscal_year` from `document_inventory.json` or `document_record.json` in input dir. Write to `visual_candidates.csv`. |
| `ESGExtractionOrchestrator` | Preserve `company`/`fiscal_year` from all input candidates. Backfill visual candidates from CSV/Table candidates sharing same `document_id`. |
| `ESGIndicatorValidation` | Pass through `company`/`fiscal_year` unchanged. |
| `ESGManualReview` | Pass through `company`/`fiscal_year` unchanged. |
| `ESGIndicatorDatabase` | Pass through. Log warning if `company` or `fiscal_year` is empty. |
| `ESGVariableDatasetBuilder` | Require `company`/`fiscal_year` for value selection. Log and count records with missing metadata. |

---

## 7. Prohibited Patterns

- Do NOT guess `company` from directory names in production code paths.
- Do NOT overwrite `fiscal_year` with any year found in a data cell or quote.
- Do NOT silently drop records with empty `company` without logging.
- Do NOT mix companies from different documents without explicit multi-document mode.
- Do NOT use `year_raw` or `year_prepared` as a substitute for `fiscal_year`.

---

## 8. Version History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-05-14 | Initial contract document |
