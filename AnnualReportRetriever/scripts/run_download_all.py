from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ajoute automatiquement la racine du projet au PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.annual_report_retriever.models import Company
from src.annual_report_retriever.retriever import AnnualReportRetriever


def get_rank(item: dict) -> str:
    """
    Récupère le rang d'un item, compatible avec les anciennes et nouvelles versions.
    """

    return str(
        item.get("rank")
        or item.get("candidate_rank")
        or item.get("source_search_rank")
        or "?"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Télécharger tous les candidats Annual Report dont le score dépasse un seuil."
    )

    parser.add_argument("--company-name", required=True)
    parser.add_argument("--fiscal-year", required=True, type=int)
    parser.add_argument("--official-domain", default=None)
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

    retriever = AnnualReportRetriever(
        root_dir=Path(args.root_dir),
    )

    result = retriever.download_high_score_candidates(
        company=company,
        fiscal_year=args.fiscal_year,
        min_score=args.min_score,
    )

    print("\n=== Download All High Score Annual Report Candidates ===")
    print(f"company_name: {result['company_name']}")
    print(f"fiscal_year: {result['fiscal_year']}")
    print(f"min_score: {result['min_score']}")
    print(f"total_raw_candidates: {result['total_raw_candidates']}")
    print(f"total_ranked_candidates: {result['total_ranked_candidates']}")
    print(f"total_selected_candidates: {result['total_selected_candidates']}")
    print(f"downloaded_count: {result['downloaded_count']}")
    print(f"failed_count: {result['failed_count']}")
    print(f"skipped_count: {result['skipped_count']}")

    print("\n--- Downloaded ---")
    for item in result["downloaded"]:
        rank = get_rank(item)
        print(f"[{rank}] score={item.get('score')} | {item.get('title')}")
        print(f"    url: {item.get('url')}")
        print(f"    local_path: {item.get('local_path')}")
        print(f"    manifest_path: {item.get('manifest_path')}")
        if item.get("resolved_from"):
            print(f"    resolved_from: {item.get('resolved_from')}")

    print("\n--- Failed ---")
    for item in result["failed"]:
        rank = get_rank(item)
        print(f"[{rank}] score={item.get('score')} | {item.get('title')}")
        print(f"    status: {item.get('download_status')}")
        print(f"    message: {item.get('message')}")
        print(f"    url: {item.get('url')}")
        if item.get("resolved_from"):
            print(f"    resolved_from: {item.get('resolved_from')}")

    print("\n--- Skipped ---")
    for item in result["skipped"]:
        rank = get_rank(item)
        print(f"[{rank}] score={item.get('score')} | {item.get('title')}")
        print(f"    decision: {item.get('decision')}")
        print(f"    reason: {item.get('reason')}")
        print(f"    url: {item.get('url')}")
        if item.get("resolved_from"):
            print(f"    resolved_from: {item.get('resolved_from')}")

    output_dir = Path(args.root_dir) / "registry"
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_company_name = (
        args.company_name
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )

    output_path = (
        output_dir
        / f"download_all_annual_report_{safe_company_name}_{args.fiscal_year}.json"
    )

    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nRapport JSON sauvegardé : {output_path}")


if __name__ == "__main__":
    main()