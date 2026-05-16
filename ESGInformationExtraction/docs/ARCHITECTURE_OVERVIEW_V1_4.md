# ESGInformationExtraction v1.4 - Architecture Overview

## Objectif

`ESGInformationExtraction` fournit un moteur documentaire PDF auditable. Son role est de transformer un PDF en representation structuree, localisee et controlee, afin de preparer une future couche ESG separee.

Le module ne valide aucune information ESG et ne produit aucun score.

## Pipeline documentaire complet

```text
PDF source
  -> document loading
  -> page extraction
  -> text block extraction
  -> block classification
  -> section detection
  -> documentary evidence store
  -> table detection
  -> figure detection
  -> multimodal inventory
  -> cross-file audit
  -> output contract validation
  -> compatibility checks
  -> batch reports
  -> remediation plan
  -> execution checklist
```

## Separation des couches

### Extraction documentaire

La couche d'extraction lit un seul PDF et produit des objets documentaires :

- document ;
- pages ;
- blocs de texte ;
- sections ;
- evidences ;
- tableaux ;
- cellules ;
- figures.

Elle ecrit uniquement dans le dossier `--output-dir`.

### Audit documentaire

La couche d'audit relit les outputs produits et verifie :

- presence des fichiers ;
- coherence des compteurs ;
- references inter-fichiers ;
- politiques de quarantine et review ;
- readiness documentaire.

Elle produit notamment `consistency_report.json`, `audit_findings.jsonl` et `document_audit_report.md`.

### Contrat de sortie

Le contrat v1.0 stabilise les fichiers, champs, valeurs autorisees et invariants.

Fichiers principaux :

- `docs/OUTPUT_CONTRACT_V1.md`
- `contracts/output_contract_v1.json`
- `tools/validate_output_contract.py`

### Batch

La couche batch ne parse pas les PDFs. Elle analyse des dossiers d'outputs existants.

Elle peut produire :

- rapport de compatibilite ;
- plan de remediation ;
- checklist d'execution humaine.

## Role des outputs principaux

- `document_record.json` : identite du document et metadonnees de chargement.
- `page_index.jsonl` : pages traitees et diagnostics texte.
- `text_blocks.jsonl` : blocs de texte localises et classes.
- `section_index.jsonl` : sections documentaires conservatives.
- `evidence_store.jsonl` : evidences documentaires non metier.
- `table_index.jsonl` / `table_cells.jsonl` : tableaux et cellules, sans interpretation ESG.
- `figure_index.jsonl` : figures et pages visuelles.
- `document_inventory.json` : resume multimodal du document.
- `multimodal_evidence_index.jsonl` : index commun texte/table/figure.
- `quality_report.jsonl` : controles qualite.
- `extraction_summary.json` : resume global d'extraction.
- `consistency_report.json` : coherence inter-fichiers.
- `document_audit_report.md` : rapport lisible par un humain.

## Pourquoi l'extraction ESG doit rester separee

Le moteur documentaire produit des objets sources fiables, localises et audites. Une extraction ESG future devra lire ces objets, mais ne doit pas etre confondue avec eux.

Cette separation evite :

- de transformer des candidats documentaires en indicateurs valides trop tot ;
- de melanger parsing PDF et interpretation metier ;
- de masquer les zones `review_required` ou `quarantine` ;
- de rendre les audits et tests plus difficiles.

Architecture future recommandee :

```text
ESGInformationExtraction outputs
  -> ESG metric candidate extraction
  -> evidence-based validation
  -> human review / quality control
  -> ESG indicator database
  -> ESG risk scoring
```

La couche ESG devra etre un module separe, avec ses propres schemas, tests et controles qualite.
