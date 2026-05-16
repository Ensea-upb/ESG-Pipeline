# SustainabilityReportRetriever

## Objectif

`SustainabilityReportRetriever` est un moteur Python spécialisé dans l’ingestion de documents ESG / Sustainability / RSE.

Son objectif est de constituer automatiquement un corpus de documents candidats à partir d’une entreprise et d’une année donnée.

```text
Entreprise A + année X
        ↓
recherche automatique de candidats
        ↓
classification et scoring initial
        ↓
téléchargement des candidats plausibles
        ↓
stockage local structuré
        ↓
création de manifests JSON