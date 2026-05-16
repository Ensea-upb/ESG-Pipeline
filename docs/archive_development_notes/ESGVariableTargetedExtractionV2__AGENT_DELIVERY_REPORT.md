# Agent Delivery Report — ESGVariableTargetedExtractionV2 v1.0

## 1. Objective

Build a new targeted extraction engine for 31 ESG variables, developed in parallel with V1.
Eliminate the main V1 failure modes: structural false positives (ISO standards, section numbers),
unit misassignment (column unit propagation errors), and low recall on visual/table content.

## 2. Why V2 is Necessary

V1 pilot results on 10 documents:
- 6,027 candidates produced
- 52.3% missing values
- 62% in unknown/boundary families
- Precision ≈ 50–55%, Recall ≈ 45–50%
- Major error types: ISO 50001/14001 extracted as values, section numbers as values,
  column units incorrectly propagated to all rows, SF6/Scope3 misclassified

V2 approach: variable-first, evidence-required, rule-based FP rejection, unit-context-aware.

## 3. Architecture Multimodale

```
DocumentV2Input (from ESGInformationExtraction)
  ├── text_blocks.jsonl     → paragraph chunks
  ├── section_index.jsonl   → section context chunks
  ├── evidence_store.jsonl  → evidence quote chunks
  ├── table_cells.jsonl     → table_layout_rebuilder → cell+header+unit context
  └── figure_index.jsonl    → visual_evidence_recovery → caption/OCR chunks
```

All chunk types flow into the hybrid retriever for variable-targeted ranking.

## 4. Compatibilité Pipeline

**Position actuelle** : Parallèle, sorties isolées dans `ESGVariableTargetedExtractionV2/outputs/`

**Position cible (Option B préférée)** :
```
ESGExtractionOrchestrator
├── csv/
├── table/
├── visual/
└── targeted_v2/   ← integration point
```

Les colonnes `targeted_candidates_v2.csv` sont alignées sur les candidats V1 pour permettre
une intégration future dans ESGIndicatorValidation sans réécriture majeure.

## 5. Embedding Backends

- `HuggingFaceEmbeddingBackend` : BAAI/bge-m3, local/offline only, ne télécharge pas pendant les tests
- `LexicalFallbackBackend` : TF-IDF like, aucune dépendance externe, toujours disponible
- `FakeEmbeddingBackend` : déterministe, tests unitaires uniquement
- Factory `get_backend()` : détection automatique + fallback transparent

## 6. Catalogue des Variables

31 variables définies dans `config/variable_semantic_catalog_v1.yaml` :
- Termes de requête EN + FR
- Unités attendues + unités interdites
- Patterns positifs + négatifs
- Patterns de faux positifs structurels
- Score minimum de pertinence
- Types de documents préférés

## 7. Outputs Produits

| Fichier | Description |
|---------|-------------|
| `document_chunks_v2.csv/jsonl` | Index de chunks multimodaux |
| `retrieval_results_v2.csv/jsonl` | Scores de retrieval par variable |
| `targeted_candidates_v2.csv/jsonl` | Candidats extraits avec lineage |
| `rejected_candidates_v2.csv` | Candidats rejetés avec raison |
| `extraction_v2_summary.json` | Résumé de l'extraction |
| `extraction_v2_quality_report.md` | Rapport qualité lisible |
| `targeted_candidates_v2_contract_validation.json` | Validation du contrat |

## 8. Tests

10 fichiers de tests, 50+ assertions, fixtures synthétiques uniquement.
Tests couvrent : catalog, chunks, embeddings, retrieval, table rebuilder,
extraction, FP rejection, contract, benchmark, non-destructif.

## 9. Limites Actuelles

- Recall visual limité sans OCR (best-effort, non-critique)
- Benchmark complet nécessite run complet sur 10 documents pilot
- Modèle HF BAAI/bge-m3 non disponible localement → fallback lexical actif
- Variables financières (market_cap, ROE, etc.) peu présentes dans rapports ESG → coverage limitée

## 10. Décision

**GO** — V2 est :
- Non destructive (zéro modification source)
- Testée (suite complète)
- Compatible output (colonnes alignées V1)
- Benchmarkable (script prêt)
- Avec fallback lexical opérationnel

Prochaine étape : run complet sur 10 documents pilot et comparaison V1 vs V2.
