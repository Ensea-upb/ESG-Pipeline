from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from dataclasses import asdict, is_dataclass
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.agm_retriever.models import Company
from src.agm_retriever.retriever import AGMRetriever


def dataclass_to_dict(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, list):
        return [dataclass_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {key: dataclass_to_dict(value) for key, value in obj.items()}
    return obj


def main() -> None:
    parser = argparse.ArgumentParser(description="Télécharger tous les documents d'assemblée générale dont le score dépasse un seuil.")

    parser.add_argument("--company-name", required=True, help="Nom de l'entreprise.")
    parser.add_argument("--fiscal-year", required=True, type=int, help="Annee cible.")
    parser.add_argument("--official-domain", default=None, help="Domaine officiel.")
    parser.add_argument("--ticker", default=None)
    parser.add_argument("--isin", default=None)
    parser.add_argument("--jurisdiction", default=None)
    parser.add_argument("--min-score", type=float, default=80.0)
    parser.add_argument("--root-dir", default="data/dossier_ingestion_0")

    args = parser.parse_args()

    company = Company(
        name=args.company_name,
        official_domain=args.official_domain,
        ticker=args.ticker,
        isin=args.isin,
        jurisdiction=args.jurisdiction,
    )

    retriever = AGMRetriever(root_dir=Path(args.root_dir))

    result = retriever.download_high_score_candidates(
        company=company,
        fiscal_year=args.fiscal_year,
        min_score=args.min_score,
    )

    print("\n=== AGMRetriever Result ===")
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

    print("\n--- Failed ---")
    for item in result.failed:
        print(f"[{item['rank']}] score={item['score']} | {item['title']}")
        print(f"    status: {item['download_status']} | {item['message']}")
        print(f"    url: {item['url']}")

    print("\n--- Skipped ---")
    for item in result.skipped:
        print(f"[{item['rank']}] score={item['score']} | {item['title']}")
        print(f"    decision: {item['decision']} | {item['reason']}")

    output_dir = Path(args.root_dir) / "registry"
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = args.company_name.lower().replace(" ", "_").replace("/", "_")
    output_path = output_dir / f"download_all_agm_{safe_name}_{args.fiscal_year}.json"

    output_path.write_text(
        json.dumps(
            {
                "company": asdict(company),
                "fiscal_year": args.fiscal_year,
                "min_score": args.min_score,
                "result": dataclass_to_dict(result),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nRapport JSON sauvegarde : {output_path}")


if __name__ == "__main__":
    main()
