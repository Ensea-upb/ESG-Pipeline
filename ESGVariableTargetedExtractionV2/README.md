# ESGVariableTargetedExtractionV2 v1.0

Variable-targeted ESG extraction engine, developed in parallel with V1.
Designed for future integration into ESGExtractionOrchestrator or as a standalone pre-processing step.

## Quick Start

```bash
# Run extraction on a single document (lexical backend, 3 variables)
python ESGVariableTargetedExtractionV2/scripts/build_targeted_extraction_v2.py \
  --input-dir "EXTERNAL_AUDIT_RUNS/.../01_information_extraction" \
  --output-dir "ESGVariableTargetedExtractionV2/outputs/smoke_test" \
  --embedding-backend lexical \
  --variables water_consumption,human_capital,co2_emissions \
  --overwrite

# Validate outputs
python ESGVariableTargetedExtractionV2/scripts/validate_targeted_extraction_v2.py \
  --output-dir "ESGVariableTargetedExtractionV2/outputs/smoke_test"

# Benchmark V1 vs V2
python ESGVariableTargetedExtractionV2/scripts/benchmark_v1_vs_v2.py \
  --v1-pilot-root "EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_10docs_v2" \
  --v2-output-root "ESGVariableTargetedExtractionV2/outputs" \
  --output-dir "ESGVariableTargetedExtractionV2/outputs/benchmark"

# Run tests
python -m pytest ESGVariableTargetedExtractionV2/tests -q
```

## Architecture

```
ESGInformationExtraction (read-only)
    ↓
input_adapter.py → DocumentV2Input
    ↓
document_chunk_index.py → chunks (text + table + visual)
    +  table_layout_rebuilder.py (unit/context)
    +  visual_evidence_recovery.py (crops/captions)
    ↓
semantic_catalog.py (31 variables)
embedding_backends.py (HF / Lexical / Fake)
    ↓
hybrid_retriever.py → retrieval_results_v2
    ↓
constrained_extractor.py → candidates (with FP rejection)
    ↓
candidate_scorer.py → scored candidates
    ↓
output_adapter.py → targeted_candidates_v2.csv/jsonl + summary
    ↓
validators.py → contract validation
```

## 31 Target Variables

Environmental (7): co2_emissions, carbon_intensity, energy_consumption, water_consumption, waste, biodiversity, fossil_exposure

Social (6): turnover, diversity, work_accidents, human_capital, supply_chain, human_rights

Governance (5): board_independence, ceo_chairman_separation, remuneration, shareholder_rights, transparency

Controversies (6): esg_scandals, fraud, corruption, pollution, lawsuits, social_controversies

Financial (7): market_cap, volatility, leverage, roa, roe, liquidity, stock_returns

## Constraints

- Never modifies ESGFinalCorpus
- Never modifies V1 pilot outputs
- No Internet calls
- No external API
- Embedding model is optional — lexical fallback always works
- All outputs go to --output-dir
