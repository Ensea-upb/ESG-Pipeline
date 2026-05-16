# DocumentPostProcessing

## Objectif

Ce module traite les documents après l’ingestion.

Les moteurs d’ingestion, comme `AnnualReportRetriever`, `SustainabilityReportRetriever` ou `ClimateReportRetriever`, ont pour rôle de collecter des documents candidats.

Ce module intervient ensuite pour :

1. centraliser les manifests ;
2. construire un registre unique des documents collectés ;
3. détecter les doublons exacts ;
4. préparer la déduplication avancée ;
5. préparer la validation documentaire ;
6. sélectionner plus tard les documents finaux exploitables.

## Séparation des responsabilités

Les retrievers font :

```text
recherche web
scoring initial
téléchargement
stockage candidates/
création des manifests