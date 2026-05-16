# Exemple concret d output ESGInformationExtraction

Source locale : `ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test/`

Cet exemple montre ce que produit le moteur documentaire PDF. Ce ne sont pas encore des indicateurs ESG : ce sont des objets documentaires structures et auditables.

## 1. Resume global

- `document_id`: `lvmh_2024_sustainability_v10_test`
- `status`: `success`
- `page_count`: `484`
- `pages_processed`: `20`
- `text_blocks_count`: `980`
- `sections_count`: `5`
- `evidence_count`: `189`
- `tables_count`: `28`
- `table_cells_count`: `4659`
- `figures_count`: `3`
- `errors_count`: `0`
- `warnings_count`: `68`
- `engine_contract_version`: `1.0.0`

## 2. DocumentRecord

```json
{
  "schema_version": "1.0.0",
  "document_id": "lvmh_2024_sustainability_v10_test",
  "sha256": "4e67ffaaae7f880fd24e837c30f10c08b0a087ca1b4314dade86e7b5d32c12cb",
  "file_name": "document.pdf",
  "page_count": 484,
  "loading_status": "readable",
  "created_at": "2026-05-10T16:42:44+00:00"
}
```

## 3. Inventaire documentaire

```json
{
  "document_id": "lvmh_2024_sustainability_v10_test",
  "page_count": 484,
  "pages_processed": 20,
  "text_blocks_count": 980,
  "sections_count": 5,
  "suspicious_sections_count": 1,
  "evidence_count": 189,
  "text_evidence_count": 166,
  "table_evidence_count": 20,
  "figure_evidence_count": 3,
  "extraction_readiness_status": "partially_ready",
  "extraction_readiness_reasons": [
    "suspicious_sections_present"
  ]
}
```

## 4. Exemples de blocs texte

- `lvmh_2024_sustainability_v10_test_page_0001_block_0001` | page `1` | type `title` | texte: "FISCAL YEAR ENDED DECEMBER 31, 2024"
- `lvmh_2024_sustainability_v10_test_page_0001_block_0002` | page `1` | type `title` | texte: "UNIVERSAL REGISTRATION DOCUMENT"
- `lvmh_2024_sustainability_v10_test_page_0002_block_0001` | page `2` | type `title` | texte: "CONTENTS"
- `lvmh_2024_sustainability_v10_test_page_0002_block_0002` | page `2` | type `toc_entry` | texte: "HISTORY 1"
- `lvmh_2024_sustainability_v10_test_page_0002_block_0003` | page `2` | type `toc_entry` | texte: "FINANCIAL HIGHLIGHTS 2"
- `lvmh_2024_sustainability_v10_test_page_0002_block_0004` | page `2` | type `toc_entry` | texte: "EXECUTIVE AND SUPERVISORY BODIES; STATUTORY AUDITORS (FROM FEBRUARY 1, 2025) 5"
- `lvmh_2024_sustainability_v10_test_page_0002_block_0005` | page `2` | type `toc_entry` | texte: "SIMPLIFIED ORGANIZATIONAL CHART OF THE GROUP AS OF DECEMBER 31, 2024 6"
- `lvmh_2024_sustainability_v10_test_page_0002_block_0006` | page `2` | type `toc_entry` | texte: "BUSINESS OVERVIEW, HIGHLIGHTS AND OUTLOOK 9"

## 5. Exemples de sections detectees

- `lvmh_2024_sustainability_v10_test_section_0001` | pages `2-3` | type `unknown` | policy `quarantine`
  - titre: "REPORT ON THE CERTIFICATION OF SUSTAINABILITY REPORTING"
- `lvmh_2024_sustainability_v10_test_section_0002` | pages `4-6` | type `general` | policy `normal`
  - titre: "FINANCIAL HIGHLIGHTS"
- `lvmh_2024_sustainability_v10_test_section_0003` | pages `7-7` | type `unknown` | policy `normal`
  - titre: "EXECUTIVE AND SUPERVISORY BODIES; STATUTORY AUDITORS"
- `lvmh_2024_sustainability_v10_test_section_0004` | pages `8-10` | type `unknown` | policy `normal`
  - titre: "SIMPLIFIED ORGANIZATIONAL CHART"
- `lvmh_2024_sustainability_v10_test_section_0005` | pages `11-20` | type `general` | policy `normal`
  - titre: "BUSINESS OVERVIEW, HIGHLIGHTS AND OUTLOOK"

## 6. Exemples d evidences documentaires

- `lvmh_2024_sustainability_v10_test_evidence_000001` | type `section_heading` | page `2` | section `lvmh_2024_sustainability_v10_test_section_0001` | review `True`
  - quote: "REPORT ON THE CERTIFICATION OF SUSTAINABILITY REPORTING"
- `lvmh_2024_sustainability_v10_test_evidence_000002` | type `section_heading` | page `4` | section `lvmh_2024_sustainability_v10_test_section_0002` | review `False`
  - quote: "FINANCIAL HIGHLIGHTS"
- `lvmh_2024_sustainability_v10_test_evidence_000003` | type `section_heading` | page `7` | section `lvmh_2024_sustainability_v10_test_section_0003` | review `True`
  - quote: "EXECUTIVE AND SUPERVISORY BODIES; STATUTORY AUDITORS"
- `lvmh_2024_sustainability_v10_test_evidence_000004` | type `section_heading` | page `8` | section `lvmh_2024_sustainability_v10_test_section_0004` | review `True`
  - quote: "SIMPLIFIED ORGANIZATIONAL CHART"
- `lvmh_2024_sustainability_v10_test_evidence_000005` | type `section_heading` | page `11` | section `lvmh_2024_sustainability_v10_test_section_0005` | review `False`
  - quote: "BUSINESS OVERVIEW, HIGHLIGHTS AND OUTLOOK"
- `lvmh_2024_sustainability_v10_test_evidence_000006` | type `paragraph` | page `2` | section `lvmh_2024_sustainability_v10_test_section_0001` | review `True`
  - quote: "As table totals are based on unrounded figures, there may be discrepancies between these totals and the sum of their rounded component figures."

## 7. Exemples de tableaux detectes

- `lvmh_2024_sustainability_v10_test_page_0001_tbl_001` | page `1` | status `low_confidence` | rows `3` | cols `1` | cells `3` | review `True`
- `lvmh_2024_sustainability_v10_test_page_0002_tbl_001` | page `2` | status `low_confidence` | rows `58` | cols `13` | cells `754` | review `True`
- `lvmh_2024_sustainability_v10_test_page_0003_tbl_001` | page `3` | status `low_confidence` | rows `60` | cols `15` | cells `900` | review `True`
- `lvmh_2024_sustainability_v10_test_page_0004_tbl_001` | page `4` | status `low_confidence` | rows `8` | cols `1` | cells `8` | review `True`
- `lvmh_2024_sustainability_v10_test_page_0004_tbl_002` | page `4` | status `empty_table` | rows `5` | cols `10` | cells `50` | review `True`

### Exemples de cellules

- `lvmh_2024_sustainability_v10_test_page_0001_tbl_001_r000_c000` | table `lvmh_2024_sustainability_v10_test_page_0001_tbl_001` | row `0` col `0` | texte: "BER 31, 2024"
- `lvmh_2024_sustainability_v10_test_page_0001_tbl_001_r001_c000` | table `lvmh_2024_sustainability_v10_test_page_0001_tbl_001` | row `1` col `0` | texte: ""
- `lvmh_2024_sustainability_v10_test_page_0001_tbl_001_r002_c000` | table `lvmh_2024_sustainability_v10_test_page_0001_tbl_001` | row `2` col `0` | texte: "DOCUMENT"
- `lvmh_2024_sustainability_v10_test_page_0002_tbl_001_r000_c000` | table `lvmh_2024_sustainability_v10_test_page_0002_tbl_001` | row `0` col `0` | texte: "C"
- `lvmh_2024_sustainability_v10_test_page_0002_tbl_001_r000_c001` | table `lvmh_2024_sustainability_v10_test_page_0002_tbl_001` | row `0` col `1` | texte: "ONTENTS"
- `lvmh_2024_sustainability_v10_test_page_0002_tbl_001_r000_c002` | table `lvmh_2024_sustainability_v10_test_page_0002_tbl_001` | row `0` col `2` | texte: ""
- `lvmh_2024_sustainability_v10_test_page_0002_tbl_001_r000_c003` | table `lvmh_2024_sustainability_v10_test_page_0002_tbl_001` | row `0` col `3` | texte: ""
- `lvmh_2024_sustainability_v10_test_page_0002_tbl_001_r000_c004` | table `lvmh_2024_sustainability_v10_test_page_0002_tbl_001` | row `0` col `4` | texte: ""

## 8. Exemples de figures/pages visuelles

- `fig_lvmh_2024_sustainability_v10_test_p0001_0000` | page `1` | type `unknown_visual` | status `detected_not_interpreted` | review `True`
  - caption: ""
- `fig_lvmh_2024_sustainability_v10_test_p0006_0000` | page `6` | type `unknown_visual` | status `detected_not_interpreted` | review `True`
  - caption: ""
- `fig_lvmh_2024_sustainability_v10_test_p0010_0000` | page `10` | type `unknown_visual` | status `detected_not_interpreted` | review `True`
  - caption: ""

## 9. Index multimodal

- `lvmh_2024_sustainability_v10_test_mm_ev_000001` | modality `text` | type `section_heading` | policy `exclude_from_automatic_extraction`
  - quote: "REPORT ON THE CERTIFICATION OF SUSTAINABILITY REPORTING"
- `lvmh_2024_sustainability_v10_test_mm_ev_000002` | modality `text` | type `section_heading` | policy `eligible_for_future_extraction`
  - quote: "FINANCIAL HIGHLIGHTS"
- `lvmh_2024_sustainability_v10_test_mm_ev_000003` | modality `text` | type `section_heading` | policy `review_before_extraction`
  - quote: "EXECUTIVE AND SUPERVISORY BODIES; STATUTORY AUDITORS"
- `lvmh_2024_sustainability_v10_test_mm_ev_000004` | modality `text` | type `section_heading` | policy `review_before_extraction`
  - quote: "SIMPLIFIED ORGANIZATIONAL CHART"
- `lvmh_2024_sustainability_v10_test_mm_ev_000005` | modality `text` | type `section_heading` | policy `eligible_for_future_extraction`
  - quote: "BUSINESS OVERVIEW, HIGHLIGHTS AND OUTLOOK"
- `lvmh_2024_sustainability_v10_test_mm_ev_000006` | modality `text` | type `paragraph` | policy `exclude_from_automatic_extraction`
  - quote: "As table totals are based on unrounded figures, there may be discrepancies between these totals and the sum of their rounded component figures."

## 10. Findings d audit

- `critical` | `file_presence` | Expected output file is missing: quality_report.jsonl.
- `critical` | `file_presence` | Expected output file is missing: extraction_summary.json.
- `info` | `id_consistency` | All evidence source references resolve to existing objects.
- `info` | `count_consistency` | Multimodal evidence index contains exactly one row per evidence_store record.
- `info` | `multimodal_policy` | No quarantined or review-required evidence is eligible for automatic future extraction.
- `minor` | `sections` | 1 suspicious section(s) are present and retained for audit.

## Lecture importante

Cet output montre que le moteur sait structurer le PDF, localiser des preuves et auditer la qualite. Il ne dit pas encore : "les emissions de LVMH valent X". Cette interpretation ESG viendra dans un module separe.
