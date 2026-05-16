# ESGCSVExtraction - Engine Completion Report

## Final Version

Version finale atteinte : v1.0.

Statut : passed avec warnings metier non bloquants.

## Versions Validees

- v0.1 : CSV global candidat.
- v0.2 : auto-audit des candidats.
- v0.3 : audit multi-documents.
- v0.4 : CSV types.
- v0.5 : observed metrics enrichis.
- v0.6 : targets enrichis.
- v0.7 : policies et risks stabilises.
- v0.8 : boundary et methodology stabilises.
- v0.9 : contrat CSV et validateur.
- v1.0 : release documentaire stable.

## Warnings

- `quality_warning=true`
- `real_world_audit_pending=true`
- `observed_metric_without_unit`: 4 sur le test LVMH.
- `target_without_target_year`: 5 sur le test LVMH.
- `visual_evidence_low_confidence`: 18 sur le test LVMH.
- Le multi-document local couvre 3 outputs, mais principalement des versions du meme document LVMH.

## Tests Executes

- `python -m compileall -q ESGCSVExtraction ESGInformationExtraction` : passed.
- `python -m pytest ESGCSVExtraction/tests --basetemp <tmp>` : 31 passed, 1 warning cache pytest.
- `python -m pytest ESGInformationExtraction/tests --basetemp <tmp>` : 228 passed, 1 warning cache pytest.

## Test Manuel LVMH

Input :

```text
ESGInformationExtraction/outputs/pdf_v10_lvmh_2024_sustainability_test
```

Output :

```text
ESGCSVExtraction/outputs/lvmh_v10_csv_test
```

Resultats :

- `source_evidences_count`: 189
- `candidates_count`: 109
- `review_required_count`: 109
- `candidate_audit_error_count`: 0
- `candidate_audit_warning_count`: 3

Distribution :

```text
boundary_context: 37
observed_metric: 26
policy_or_commitment: 16
methodology_context: 3
target: 7
risk_statement: 2
visual_evidence: 18
```

## CSV Produits

- `esg_information_candidates.csv`
- `esg_information_candidates.jsonl`
- `observed_metrics.csv`
- `targets.csv`
- `policies.csv`
- `risks.csv`
- `boundary_contexts.csv`
- `methodology_contexts.csv`
- `visual_evidences.csv`
- `extraction_audit.csv`
- `candidate_audit_summary.json`
- `candidate_audit_findings.jsonl`
- `candidate_audit_samples.csv`
- `extraction_summary.json`

## Validation Contrat CSV

Commande :

```powershell
python ESGCSVExtraction/scripts/validate_csv_outputs.py `
  --output-dir "ESGCSVExtraction/outputs/lvmh_v10_csv_test" `
  --contract-path "ESGCSVExtraction/contracts/csv_output_contract_v0.json"
```

Resultat :

```text
status: success
contract_version: 0.9.0
checks_count: 240
errors_count: 0
warnings_count: 0
```

## Audit Multi-documents

Output :

```text
ESGCSVExtraction/outputs/multi_document_v10
```

Resultats :

- `documents_tested_count`: 3
- `total_candidates_count`: 327

Distribution agregee :

```text
boundary_context: 111
observed_metric: 78
policy_or_commitment: 48
methodology_context: 9
target: 21
risk_statement: 6
visual_evidence: 54
```

## Preuve Non Destructive

LVMH input :

```text
files_hashed: 23
digest_before: 0face05c2ac75cb70b07c6b6a002d496304af685f2091957aeef37e37c1352ee
digest_after:  0face05c2ac75cb70b07c6b6a002d496304af685f2091957aeef37e37c1352ee
```

Outputs `ESGInformationExtraction` :

```text
files_hashed: 276
digest_before: 1ab643ab37810064c3e44f9411c279d151ccf3d88e04758984820d3c5ab5ec90
digest_after:  1ab643ab37810064c3e44f9411c279d151ccf3d88e04758984820d3c5ab5ec90
```

## Garanties

- Aucun input documentaire modifie.
- Aucun PDF relu ou modifie.
- Aucun score ESG.
- Aucun indicateur valide.
- Tous les resultats restent `candidate_only`.
- Tous les resultats restent `review_required=true`.
- `confidence <= 0.6`.

## Limites Restantes

- Extraction par regles simples, donc faux positifs possibles.
- Unites et annees cibles encore incompletes.
- Figures et tableaux non interpretes.
- Pas de reconciliation multi-annees.
- Pas de validation metier ESRS/GRI.

## Recommandation

Prochaine etape recommandee : v1.1 de revue qualite sur corpus diversifie CAC40, avec enrichissement des tests reels multi-entreprises avant toute couche de validation ESG.
