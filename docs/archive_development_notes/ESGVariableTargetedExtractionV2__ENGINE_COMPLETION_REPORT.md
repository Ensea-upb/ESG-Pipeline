# Engine Completion Report — ESGVariableTargetedExtractionV2 v1.0

## Status: COMPLETE

All modules delivered, tested, and validated as of 2026-05-15.

---

## Module Inventory

| Module | File | Status | Tests |
|--------|------|--------|-------|
| Config | `src/.../config.py` | ✓ | via catalog |
| IO Utils | `src/.../io_utils.py` | ✓ | via integration |
| Semantic Catalog | `src/.../semantic_catalog.py` | ✓ | test_semantic_catalog_v01 |
| Input Adapter | `src/.../input_adapter.py` | ✓ | via integration |
| Document Chunk Index | `src/.../document_chunk_index.py` | ✓ | test_chunk_index_v02 |
| Embedding Backends | `src/.../embedding_backends.py` | ✓ | test_embedding_backends_v03 |
| Hybrid Retriever | `src/.../hybrid_retriever.py` | ✓ | test_hybrid_retrieval_v04 |
| Table Layout Rebuilder | `src/.../table_layout_rebuilder.py` | ✓ | test_table_layout_rebuilder_v05 |
| Visual Evidence Recovery | `src/.../visual_evidence_recovery.py` | ✓ | test_non_destructive_v10 |
| Constrained Extractor | `src/.../constrained_extractor.py` | ✓ | test_constrained_extractor_v06 |
| Candidate Scorer | `src/.../candidate_scorer.py` | ✓ | via extractor tests |
| Output Adapter | `src/.../output_adapter.py` | ✓ | test_output_contract_v08 |
| Validators | `src/.../validators.py` | ✓ | test_output_contract_v08 |
| Benchmark | `src/.../benchmark.py` | ✓ | test_benchmark_v09 |

## Script Inventory

| Script | Purpose | Status |
|--------|---------|--------|
| `scripts/build_targeted_extraction_v2.py` | Full pipeline CLI | ✓ |
| `scripts/validate_targeted_extraction_v2.py` | Contract validation | ✓ |
| `scripts/benchmark_v1_vs_v2.py` | V1 vs V2 comparison | ✓ |

## Test Inventory

| File | Scope | Assertions |
|------|-------|-----------|
| `test_semantic_catalog_v01.py` | 31 variables, units, domains | 12 tests |
| `test_chunk_index_v02.py` | Chunking, metadata, deduplication | 10 tests |
| `test_embedding_backends_v03.py` | FakeBackend, Lexical, HF offline | 11 tests |
| `test_hybrid_retrieval_v04.py` | Scores, top-k, variable ranking | 8 tests |
| `test_table_layout_rebuilder_v05.py` | Unit context, conflict detection | 8 tests |
| `test_constrained_extractor_v06.py` | Value/unit extraction, lineage | 10 tests |
| `test_false_positive_rejection_v07.py` | ISO, section, page, footnote | 8 tests |
| `test_output_contract_v08.py` | Contract validation, file output | 9 tests |
| `test_benchmark_v09.py` | Benchmark report, summary | 6 tests |
| `test_non_destructive_v10.py` | No source modification | 7 tests |

**Total: 10 test files, 89 test functions**

---

## Variable Coverage

### Environmental (7)
- `co2_emissions` — Scope 1/2/3, GHG, ktCO2e, MtCO2e, tCO2e
- `carbon_intensity` — tCO2e/revenue, tCO2e/employee, intensity indices
- `energy_consumption` — GWh, TWh, PJ, MWh, renewable share %
- `water_consumption` — Mm3, m3, ML, water withdrawal/discharge
- `waste` — tonnes, kt, recycling rate %, hazardous waste
- `biodiversity` — hectares, sites, biodiversity score, TNFD
- `fossil_exposure` — % revenue fossil, stranded assets, green revenue

### Social (6)
- `turnover` — attrition %, voluntary/involuntary turnover
- `diversity` — gender %, women in leadership, pay gap
- `work_accidents` — TRIR, LTIR, fatalities, lost-time accidents
- `human_capital` — training hours, headcount, employees, FTE
- `supply_chain` — supplier audits, ESG supplier %, CSRD coverage
- `human_rights` — ILO compliance, modern slavery, forced labor

### Governance (5)
- `board_independence` — % independent directors, non-exec ratio
- `ceo_chairman_separation` — dual role, combined/separate leadership
- `remuneration` — CEO/median ratio, variable pay, ESG-linked bonus
- `shareholder_rights` — voting rights, say-on-pay, minority rights
- `transparency` — ESG reporting index, GRI/SASB alignment, assurance

### Controversies (6)
- `esg_scandals` — RepRisk score, controversy events
- `fraud` — accounting fraud, financial irregularities
- `corruption` — FCPA, anti-bribery, GRECO compliance
- `pollution` — spills, fine amounts, NOx/SOx, superfund
- `lawsuits` — legal proceedings, penalties, class actions
- `social_controversies` — labor disputes, community conflicts

### Financial (7)
- `market_cap` — market capitalization, enterprise value
- `volatility` — beta, 30-day/annualized vol
- `leverage` — debt/equity, net debt/EBITDA, gearing ratio
- `roa` — return on assets, asset efficiency
- `roe` — return on equity, shareholder return
- `liquidity` — current ratio, quick ratio, cash equivalents
- `stock_returns` — TSR, 1Y/3Y/5Y returns

---

## Anti-False-Positive Guarantees

The following patterns are **never** extracted as values:

| Pattern | Example | Rule |
|---------|---------|------|
| ISO standard codes | `50001`, `14001`, `45001` | `^\d{5}$` + context |
| Section numbers | `2.1`, `3.4.2` | `^\d{1,2}\.\d{1,2}(\.\d+)?$` |
| Page numbers | `Page 42`, `p. 127` | page context detection |
| Footnote markers | `(1)`, `[2]`, `¹` | footnote context detection |
| Bare integers | `27` without unit | requires unit in context |

---

## Embedding Strategy

```
Priority 1: HuggingFaceEmbeddingBackend (BAAI/bge-m3, 1024-dim)
  → Requires: sentence-transformers installed + model cached
  → Mode: offline_mode=True (never downloads)

Priority 2: LexicalFallbackBackend (TF-IDF, 128-dim)
  → Always available, no external dependencies
  → Adequate for keyword-heavy ESG text

Priority 3: FakeEmbeddingBackend (SHA-256, 64-dim)
  → Tests only, deterministic, never use in production
```

---

## Output Schema Version

All outputs tagged with `schema_version: "2.0.0"` in extraction_v2_summary.json.
Candidate columns are aligned with V1 pilot output for zero-migration future integration.

---

## Known Limitations

1. **Visual recall**: OCR best-effort; pytesseract/easyocr optional; captions always processed
2. **Financial variables**: Low coverage in sustainability reports (by design — market data not in PDFs)
3. **HF model**: Not cached locally → lexical fallback active by default
4. **Benchmark completeness**: Requires full 10-document run to compute aggregate P/R metrics
5. **Language**: EN+FR query terms; DE/ES/IT documents will have lower recall

---

## Non-Destructive Guarantees

- Zero writes to `ESGFinalCorpus/`
- Zero writes to `EXTERNAL_AUDIT_RUNS/`
- Zero writes to any existing V1 module directory
- All outputs exclusively in `ESGVariableTargetedExtractionV2/outputs/`
- Verified by `test_non_destructive_v10.py`
