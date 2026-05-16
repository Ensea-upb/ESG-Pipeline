# ESGInformationExtraction v1.4 - Validation Commands

Toutes les commandes ci-dessous sont donnees pour Windows PowerShell depuis la racine du projet :

```powershell
cd C:\Users\hp\Desktop\ESG
```

## 1. Compilation Python

```powershell
python -m compileall -q ESGInformationExtraction
```

Resultat attendu : code 0, pas de sortie.

## 2. Suite de tests complete

```powershell
$bt = Join-Path $env:TEMP ('pytest_esg_' + [guid]::NewGuid().ToString())
python -m pytest ESGInformationExtraction\tests --basetemp $bt
```

Resultat attendu pour v1.4 :

- `228 passed`
- `0 failed`
- `0 errors`

## 3. Extraction documentaire LVMH

Exemple de relance sur un seul PDF, sans extraction massive :

```powershell
python ESGInformationExtraction/run_pdf_extraction.py `
  --pdf-path "C:\Users\hp\Desktop\ESG\ESGFinalCorpus\lvmh\2024\02_sustainability_statement_csrd_esrs\document.pdf" `
  --document-id "lvmh_2024_sustainability_v14_test" `
  --output-dir "ESGInformationExtraction\outputs\pdf_v14_lvmh_2024_sustainability_test" `
  --max-pages 20 `
  --overwrite
```

## 4. Validation du contrat v1.0

```powershell
python ESGInformationExtraction/tools/validate_output_contract.py `
  --output-dir "ESGInformationExtraction\outputs\pdf_v10_lvmh_2024_sustainability_test" `
  --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"
```

## 5. Audit documentaire standalone

```powershell
python ESGInformationExtraction/tools/run_document_audit.py `
  --output-dir "ESGInformationExtraction\outputs\pdf_v10_lvmh_2024_sustainability_test" `
  --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" `
  --overwrite
```

Cette commande regenere uniquement :

- `consistency_report.json`
- `audit_findings.jsonl`
- `document_audit_report.md`

## 6. Compatibilite d'un output

```powershell
python ESGInformationExtraction/tools/check_output_compatibility.py `
  --output-dir "ESGInformationExtraction\outputs\pdf_v10_lvmh_2024_sustainability_test" `
  --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json"
```

## 7. Batch compatibility

```powershell
python ESGInformationExtraction/tools/batch_check_outputs.py `
  --outputs-root "ESGInformationExtraction\outputs" `
  --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" `
  --write-report `
  --overwrite
```

Fichiers attendus :

- `batch_compatibility_summary.json`
- `batch_compatibility_table.csv`
- `batch_compatibility_report.md`

## 8. Batch remediation

```powershell
python ESGInformationExtraction/tools/batch_check_outputs.py `
  --outputs-root "ESGInformationExtraction\outputs" `
  --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" `
  --write-report `
  --write-remediation-plan `
  --overwrite
```

Fichiers attendus :

- `batch_remediation_plan.json`
- `batch_remediation_plan.csv`
- `batch_remediation_plan.md`

## 9. Batch execution checklist

```powershell
python ESGInformationExtraction/tools/batch_check_outputs.py `
  --outputs-root "ESGInformationExtraction\outputs" `
  --contract-path "ESGInformationExtraction\contracts\output_contract_v1.json" `
  --write-report `
  --write-remediation-plan `
  --write-execution-checklist `
  --overwrite
```

Fichiers attendus :

- `batch_execution_checklist.json`
- `batch_execution_checklist.csv`
- `batch_execution_checklist.md`

## 10. Rappels de perimetre

Ces commandes ne doivent pas etre confondues avec une extraction ESG.

La v1.4 ne produit pas :

- metriques ESG ;
- indicateurs ;
- score ;
- RAG ;
- base vectorielle ;
- OCR massif ;
- interpretation metier des tableaux ou figures.
