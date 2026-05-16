from __future__ import annotations

BUSINESS_STEPS = {
    "ESGInformationExtraction": {
        "name": "Lecture et structuration du PDF",
        "description": "Le document est lu, découpé en pages, sections, textes, tableaux et images.",
        "order": 1,
    },
    "ESGCSVExtraction": {
        "name": "Extraction des informations candidates",
        "description": "Le système repère les informations utiles dans le texte.",
        "order": 2,
    },
    "ESGTableExtraction": {
        "name": "Extraction des informations candidates",
        "description": "Le système repère les informations utiles dans les tableaux.",
        "order": 2,
    },
    "ESGVisualExtraction": {
        "name": "Extraction des informations candidates",
        "description": "Le système repère les informations utiles dans les images.",
        "order": 2,
    },
    "ESGExtractionOrchestrator": {
        "name": "Consolidation des résultats",
        "description": "Les informations candidates sont rassemblées dans un fichier unique.",
        "order": 3,
    },
    "ESGIndicatorValidation": {
        "name": "Pré-validation des candidats",
        "description": "Les candidats sont classés en informations possibles, à revoir ou à rejeter.",
        "order": 4,
    },
    "ESGManualReview": {
        "name": "Revue humaine",
        "description": "L’utilisateur vérifie les candidats et prend une décision explicite. accept_candidate n’est pas un indicateur final.",
        "order": 5,
    },
    "ESGManualReviewApply": {
        "name": "Application des décisions humaines",
        "description": "Les décisions humaines sont appliquées et auditées sans créer d’indicateur final.",
        "order": 5,
    },
    "ESGIndicatorDatabase": {
        "name": "Base préparatoire d’indicateurs",
        "description": "Les candidats acceptés sont organisés dans une base préparatoire, non finale.",
        "order": 6,
    },
}

STATUS_LABELS = {
    "ready": "Terminé",
    "missing": "Non lancé",
    "success": "Terminé",
    "failed": "Erreur",
    "timeout": "Erreur",
    "dry_run": "Simulation effectuée",
    "not_run": "Non lancé",
    "planned": "Préparé",
}

WARNINGS = {
    "missing_expected_files": "Des fichiers attendus ne sont pas encore produits.",
    "empty_csv": "Un fichier CSV est vide.",
    "stderr_not_empty": "Un run contient des messages d’erreur ou d’avertissement.",
    "preparation_only": "La base est préparatoire : aucun indicateur ESG final validé.",
}


def get_business_step_name(technical_module_name: str) -> str:
    return BUSINESS_STEPS.get(technical_module_name, {}).get("name", technical_module_name)


def get_business_step_description(technical_module_name: str) -> str:
    return BUSINESS_STEPS.get(technical_module_name, {}).get("description", "Étape de traitement ESG candidate-only.")


def get_business_step_order() -> list[str]:
    return [k for k, _ in sorted(BUSINESS_STEPS.items(), key=lambda item: (item[1]["order"], item[0]))]


def get_business_status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status or "Inconnu")


def get_business_warning_message(code: str) -> str:
    return WARNINGS.get(code, code)
