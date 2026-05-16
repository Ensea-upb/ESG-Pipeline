from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from dataclasses import asdict, is_dataclass
from typing import Any

# Ajoute automatiquement la racine du projet au PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.climate_report_retriever.models import Company
from src.climate_report_retriever.retriever import ClimateReportRetriever


def dataclass_to_dict(obj: Any) -> Any:
    """
    Convertit récursivement les dataclasses en dictionnaires.
    """

    if is_dataclass(obj):
        return asdict(obj)

    if isinstance(obj, list):
        return [dataclass_to_dict(item) for item in obj]

    if isinstance(obj, dict):
        return {key: dataclass_to_dict(value) for key, value in obj.items()}

    return obj


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Télécharger tous les candidats rapports climat / TCFD / transition "
            "dont le score dépasse un seuil."
        )
    )

    parser.add_argument(
        "--company-name",
        required=True,
        help="Nom de l'entreprise. Exemple : TotalEnergies",
    )

    parser.add_argument(
        "--fiscal-year",
        required=True,
        type=int,
        help="Année cible. Exemple : 2024",
    )

    parser.add_argument(
        "--official-domain",
        default=None,
        help="Domaine officiel. Exemple : totalenergies.com",
    )

    parser.add_argument(
        "--ticker",
        default=None,
        help="Ticker. Exemple : TTE",
    )

    parser.add_argument(
        "--isin",
        default=None,
        help="ISIN. Exemple : FR0000120271",
    )

    parser.add_argument(
        "--jurisdiction",
        default=None,
        help="Juridiction. Exemple : France",
    )

    parser.add_argument(
        "--min-score",
        type=float,
        default=80.0,
        help="Score minimal pour télécharger un candidat. Défaut : 80.",
    )

    parser.add_argument(
        "--root-dir",
        default="data/dossier_ingestion_0",
        help="Dossier racine de stockage.",
    )

    args = parser.parse_args()

    company = Company(
        name=args.company_name,
        official_domain=args.official_domain,
        ticker=args.ticker,
        isin=args.isin,
        jurisdiction=args.jurisdiction,
    )

    retriever = ClimateReportRetriever(
        root_dir=Path(args.root_dir),
    )

    result = retriever.download_high_score_candidates(
        company=company,
        fiscal_year=args.fiscal_year,
        min_score=args.min_score,
    )

    print("\n=== Climate Report Retriever Result ===")
    print(f"status: {result.status}")
    print(f"message: {result.message}")
    print(f"company_name: {result.company_name}")
    print(f"fiscal_year: {result.fiscal_year}")
    print(f"downloaded_count: {result.downloaded_count}")
    print(f"failed_count: {result.failed_count}")
    print(f"skipped_count: {result.skipped_count}")

    print("\n--- Downloaded ---")
    for item in result.downloaded:
        print(f"[{item['rank']}] score={item['score']} | {item['title']}")
        print(f"    url: {item['url']}")
        print(f"    local_path: {item['local_path']}")
        print(f"    manifest_path: {item['manifest_path']}")

    print("\n--- Failed ---")
    for item in result.failed:
        print(f"[{item['rank']}] score={item['score']} | {item['title']}")
        print(f"    status: {item['download_status']}")
        print(f"    message: {item['message']}")
        print(f"    url: {item['url']}")

    print("\n--- Skipped ---")
    for item in result.skipped:
        print(f"[{item['rank']}] score={item['score']} | {item['title']}")
        print(f"    decision: {item['decision']}")
        print(f"    reason: {item['reason']}")
        print(f"    url: {item['url']}")

    output_dir = Path(args.root_dir) / "registry"
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_company_name = args.company_name.lower().replace(" ", "_").replace("/", "_")

    output_path = (
        output_dir
        / f"download_all_climate_{safe_company_name}_{args.fiscal_year}.json"
    )

    output_payload = {
        "company": asdict(company),
        "fiscal_year": args.fiscal_year,
        "min_score": args.min_score,
        "result": dataclass_to_dict(result),
    }

    output_path.write_text(
        json.dumps(output_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nRapport JSON sauvegardé : {output_path}")


if __name__ == "__main__":
    main()
