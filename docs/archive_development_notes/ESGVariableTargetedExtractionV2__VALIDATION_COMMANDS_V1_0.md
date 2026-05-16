# Validation Commands — ESGVariableTargetedExtractionV2 v1.0

## 1. Tests unitaires

```bash
cd C:\Users\hp\Desktop\ESG
python -m pytest ESGVariableTargetedExtractionV2/tests -q
```

## 2. Tests sans cache provider

```bash
python -m pytest ESGVariableTargetedExtractionV2/tests -q -p no:cacheprovider
```

## 3. Tests globaux (régression)

```bash
python -m pytest --basetemp .pytest_tmp_v2 -p no:cacheprovider -q
```

## 4. Smoke test sur données réelles (TotalEnergies 2024 URD)

Trouver le document_id :
```bash
ls EXTERNAL_AUDIT_RUNS\strict_pilot_prepare_review_10docs_v2\totalenergies\2024\01_urd_annual_report\
```

Lancer l'extraction V2 :
```bash
python ESGVariableTargetedExtractionV2/scripts/build_targeted_extraction_v2.py ^
  --input-dir "EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_10docs_v2/totalenergies/2024/01_urd_annual_report/<doc_id>/01_information_extraction" ^
  --output-dir "ESGVariableTargetedExtractionV2/outputs/totalenergies_2024_urd_v2_smoke" ^
  --embedding-backend lexical ^
  --variables water_consumption,human_capital,co2_emissions,energy_consumption,diversity ^
  --overwrite
```

## 5. Validation du contrat

```bash
python ESGVariableTargetedExtractionV2/scripts/validate_targeted_extraction_v2.py ^
  --output-dir "ESGVariableTargetedExtractionV2/outputs/totalenergies_2024_urd_v2_smoke" ^
  --contract-path "ESGVariableTargetedExtractionV2/contracts/targeted_candidates_v2_contract.json"
```

## 6. Benchmark V1 vs V2

Après avoir run V2 sur les 10 documents :
```bash
python ESGVariableTargetedExtractionV2/scripts/benchmark_v1_vs_v2.py ^
  --v1-pilot-root "EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_10docs_v2" ^
  --v2-output-root "ESGVariableTargetedExtractionV2/outputs" ^
  --manual-baseline "ESGVariableTargetedExtractionV2/benchmarks/schneider_tcfd_2023_manual_baseline_template.csv" ^
  --output-dir "ESGVariableTargetedExtractionV2/outputs/benchmark_v1_vs_v2"
```

## Critères de succès du smoke test

- [ ] Output directory créé
- [ ] `targeted_candidates_v2.csv` présent et non vide
- [ ] `extraction_v2_summary.json` présent
- [ ] `company` et `fiscal_year` présents dans tous les candidats
- [ ] `quote` non vide pour tous les `candidate_found`
- [ ] Aucun crash si embeddings HF indisponibles
- [ ] Validation du contrat : status = ok ou warning (pas failed)
- [ ] Aucun fichier modifié dans `01_information_extraction`
