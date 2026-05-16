from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .output_discovery import discover_outputs
from .demo_data import DEMO_COMPANY, DEMO_DOCUMENT, DEMO_YEAR


@dataclass(frozen=True)
class BusinessDocument:
    company: str
    fiscal_year: str
    document_label: str
    document_id: str
    document_type: str
    input_dir: str
    detected_status: str
    technical_details: dict[str, Any]


def _fallback(value: Any, fallback: str) -> str:
    if value in (None, "", "nan"):
        return fallback
    return str(value)


def build_business_documents(project_root: str | Path = ".") -> list[BusinessDocument]:
    docs: list[BusinessDocument] = []
    for item in discover_outputs(project_root):
        if item["module_name"] != "ESGInformationExtraction":
            continue
        output_dir = Path(item["output_dir"])
        document_id = _fallback(item.get("document_id"), output_dir.name)
        company = _fallback(item.get("company"), "Entreprise inconnue")
        fiscal_year = _fallback(item.get("fiscal_year"), "Année inconnue")
        document_type = "Document ESG"
        label = f"{company} - {fiscal_year} - {document_id}"
        docs.append(BusinessDocument(
            company=company,
            fiscal_year=fiscal_year,
            document_label=label,
            document_id=document_id,
            document_type=document_type,
            input_dir=str(output_dir),
            detected_status=item.get("detected_status", "detected"),
            technical_details=item,
        ))
    return docs


def build_demo_business_document(project_root: str | Path = ".") -> BusinessDocument:
    root = Path(project_root).resolve() / "ESGProductionControlCenter" / "outputs" / "demo" / "demo_company_2024"
    return BusinessDocument(
        company=DEMO_COMPANY,
        fiscal_year=DEMO_YEAR,
        document_label=f"{DEMO_COMPANY} - {DEMO_YEAR} - {DEMO_DOCUMENT}",
        document_id="demo_luxury_group_2024_sustainability_statement",
        document_type=DEMO_DOCUMENT,
        input_dir=str(root),
        detected_status="demo_synthetic",
        technical_details={
            "demo_data": True,
            "synthetic_source": True,
            "output_dir": str(root),
            "warning": "Données synthétiques — démonstration uniquement.",
        },
    )


def get_companies(documents: list[BusinessDocument]) -> list[str]:
    return sorted({d.company for d in documents}) or ["Entreprise inconnue"]


def get_years(documents: list[BusinessDocument], company: str) -> list[str]:
    return sorted({d.fiscal_year for d in documents if d.company == company}) or ["Année inconnue"]


def filter_documents(documents: list[BusinessDocument], company: str, fiscal_year: str) -> list[BusinessDocument]:
    return [d for d in documents if d.company == company and d.fiscal_year == fiscal_year]
