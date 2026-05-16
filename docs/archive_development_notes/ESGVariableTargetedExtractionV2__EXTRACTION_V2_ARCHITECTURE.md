# ESGVariableTargetedExtractionV2 — Architecture Reference

## Design Philosophy

V2 inverts the V1 extraction flow:

```
V1 (document-first):  document → all chunks → all values → classify variable
V2 (variable-first):  variable → targeted retrieval → constrained extraction → validated candidate
```

This inversion eliminates the two main V1 failure modes:
- **Structural FPs**: ISO codes, section numbers, page numbers extracted as numeric values
- **Unit misassignment**: Column unit propagated to every row (e.g., "27 → 27 tonnes" for a % column)

---

## Component Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ESGInformationExtraction                            │
│  (read-only source — never modified)                                        │
│  text_blocks.jsonl  section_index.jsonl  evidence_store.jsonl               │
│  table_cells.jsonl  table_index.jsonl    figure_index.jsonl                 │
└───────────────────────────┬─────────────────────────────────────────────────┘
                            │ load_document_input()
                            ▼
┌───────────────────────────────────────────────────────────┐
│               DocumentV2Input (dataclass)                  │
│  company, fiscal_year, official_doc_type, final_path       │
│  text_blocks, section_index, evidence_store                │
│  table_cells, table_index, figure_index                    │
└────────┬──────────────────┬────────────────────┬──────────┘
         │                  │                    │
         ▼                  ▼                    ▼
  text/section/      TableLayout           VisualEvidence
  evidence chunks    Rebuilder             Recovery
  (paragraph)        (cell+header          (caption/OCR
                     +unit context)        chunks)
         │                  │                    │
         └──────────────────┴────────────────────┘
                            │ build_all_chunks()
                            ▼
┌───────────────────────────────────────────────────────────┐
│              DocumentChunkIndex (DataFrame)                │
│  chunk_id, source_type, text, page_number, unit_context   │
│  iso_noise, section_noise, table_context, visual_warning  │
│  company, fiscal_year, document_id, doc_type              │
└───────────────────────────┬───────────────────────────────┘
                            │
           ┌────────────────┼────────────────────┐
           │                │                    │
           ▼                ▼                    ▼
     SemanticCatalog  EmbeddingBackend    for each variable:
     (31 variables)   encode(all_chunks)  retrieve_for_variable()
                            │
                            ▼
┌───────────────────────────────────────────────────────────┐
│              HybridRetriever                               │
│  score = emb_w * cos_sim                                   │
│         + kw_w  * keyword_match                            │
│         + unit_w * unit_coherence                          │
│         + sec_w  * section_boost                           │
│         - structural_penalty (ISO/section/page/footnote)   │
└───────────────────────────┬───────────────────────────────┘
                            │ top-k chunks per variable
                            ▼
┌───────────────────────────────────────────────────────────┐
│              ConstrainedExtractor                          │
│  • Extracts (value, unit, year) from each chunk            │
│  • Rejects: ISO codes, section numbers, page numbers       │
│  • Validates unit-variable coherence                       │
│  • Maps variable: MtCO2e→co2_emissions, Mm3→water, etc.  │
│  • Produces candidates with full lineage                   │
└───────────────────────────┬───────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────┐
│              CandidateScorer                               │
│  candidate_score =                                         │
│    0.40 * retrieval_score                                  │
│  + 0.35 * extraction_quality                               │
│  + 0.25 * context_quality                                  │
│  - structural_penalty                                      │
│  - unit_mismatch_penalty                                   │
└───────────────────────────┬───────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────┐
│              OutputAdapter                                  │
│  targeted_candidates_v2.csv/jsonl                          │
│  rejected_candidates_v2.csv                                │
│  retrieval_results_v2.csv/jsonl                            │
│  document_chunks_v2.csv/jsonl                              │
│  extraction_v2_summary.json                                │
│  extraction_v2_quality_report.md                           │
└───────────────────────────┬───────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────┐
│              Validators                                     │
│  targeted_candidates_v2_contract_validation.json           │
│  status: ok | warning | failed                             │
└───────────────────────────────────────────────────────────┘
```

---

## Data Flow: Single Variable

Example: `water_consumption`

```
1. SemanticCatalog.get_variable_config("water_consumption")
   → query_terms: ["water consumption", "water withdrawal", "consommation eau", ...]
   → expected_units: ["Mm3", "m3", "ML", "thousand m3", ...]
   → forbidden_units: ["MtCO2e", "ktCO2e", "employees", ...]
   → fp_patterns: ["ISO 14001", "section \\d+\\.\\d+"]

2. HybridRetriever.retrieve_for_variable("water_consumption", chunks, top_k=10)
   → Scores all chunks
   → Applies structural penalties
   → Returns top-10 by score

3. ConstrainedExtractor.extract_candidates(retrieval_results, "water_consumption")
   → For each chunk:
      a. Extract (value, unit, year) using regex
      b. Reject if ISO code: False → continue
      c. Reject if section number: False → continue
      d. Validate unit: "Mm3" in expected_units → True
      e. Map variable: confirmed = water_consumption
      f. Produce candidate with status="candidate_found"

4. CandidateScorer.score(candidate)
   → retrieval_score=0.82, extraction_quality=0.90, context_quality=0.75
   → candidate_score=0.83
   → score_reason="Strong unit match (Mm3), clear value, relevant section"
```

---

## Chunk Types

| Type | Source | Key Extra Fields |
|------|--------|-----------------|
| `text_block` | text_blocks.jsonl | paragraph text, page |
| `section` | section_index.jsonl | section_title, section_level |
| `evidence` | evidence_store.jsonl | quote, confidence |
| `table_cell` | table_cells.jsonl | row_header, col_header, unit_context |
| `figure_caption` | figure_index.jsonl | caption, detection_method |

All chunk types share: `chunk_id`, `document_id`, `company`, `fiscal_year`, `page_number`, `text`, `source_type`, `doc_type`

---

## Embedding Backends

```python
# Priority order in get_backend()
1. HuggingFaceEmbeddingBackend  # if sentence-transformers + model cached
2. LexicalFallbackBackend       # always available, no deps
3. FakeEmbeddingBackend         # tests only
```

### Score Composition

```
embedding_score = cosine_similarity(query_embedding, chunk_embedding)
keyword_score   = matches(query_terms + positive_patterns) / total_terms
unit_score      = 1.0 if expected_unit in chunk_text else 0.0
section_score   = 0.1 if doc_type in preferred_doc_types else 0.0
penalty         = -0.3 if ISO_pattern else -0.2 if section_number else 0.0

final_score = 0.60*embedding + 0.25*keyword + 0.10*unit + 0.05*section - penalty
```

---

## Candidate Output Schema

```
targeted_candidates_v2.csv columns (16 required + optional):

Required:
  document_id, company, fiscal_year, official_doc_type, final_path,
  variable_name, indicator_family, domain,
  candidate_status, candidate_score,
  value, unit, raw_year,
  quote, page_number, chunk_id

Optional:
  retrieval_score, extraction_quality, context_quality,
  score_components, score_reason,
  table_context, visual_warning, lineage, rejection_reason,
  row_header, col_header, unit_context, detection_method
```

### Candidate Statuses

| Status | Meaning |
|--------|---------|
| `candidate_found` | Value extracted with evidence |
| `no_evidence_found` | No relevant chunk above threshold |
| `value_not_found` | Relevant chunks found, no extractable value |
| `unit_mismatch` | Value found, unit doesn't match variable |
| `fp_rejected` | FP pattern detected (ISO/section/page/footnote) |
| `below_threshold` | Score < min_relevance_score |
| `extraction_error` | Unexpected error (logged, non-fatal) |

---

## Table Layout Rebuilder Detail

V1 failure mode: `table_cells.jsonl` has individual cells; extracting "27" from row 3 col 2 without knowing col header is "%" and row unit is "%" leads to "27 → 27 tonnes" if the table has a unit row elsewhere.

V2 fix:

```python
TableContextChunk:
  cell_value: "27"
  col_header: "Share of renewable energy"
  row_header: "2024"
  unit_context: "%"           # derived from: cell > col_header > row_header > table title
  unit_conflict: False        # col says "%" and row says "%" → consistent
  probable_footnote: False    # 27 is not a single digit
  iso_standard_detected: False
  section_number_detected: False
  
  → text = "Share of renewable energy 2024: 27 % [col: Share of renewable energy | row: 2024 | unit: %]"
```

---

## Integration Roadmap

```
Current (v1.0):
  ESGExtractionOrchestrator
    ├── csv/
    ├── table/
    └── visual/

  ESGVariableTargetedExtractionV2/outputs/   ← standalone, parallel

Target (Option B, future):
  ESGExtractionOrchestrator
    ├── csv/
    ├── table/
    ├── visual/
    └── targeted_v2/   ← integration point
         targeted_candidates_v2.csv
         extraction_v2_summary.json
```

Integration requires: calling `build_targeted_extraction_v2.py` from orchestrator, writing outputs to `<run_root>/targeted_v2/`, and optionally passing candidates to ESGIndicatorValidation.

Column alignment between `targeted_candidates_v2.csv` and V1 candidate schema is maintained deliberately to enable this future step.
