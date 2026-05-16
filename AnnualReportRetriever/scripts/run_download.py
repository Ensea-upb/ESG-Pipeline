from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ajoute automatiquement la racine du projet au PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.annual_report_retriever.models import Company
from src.annual_report_retriever.retriever import AnnualReportRetriever


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Télécharger automatiquement le rapport annuel d'une entreprise."
    )

    parser.add_argument(
        "--company-name",
        required=True,
        help="Nom de l'entreprise. Exemple : LVMH",
    )

    parser.add_argument(
        "--fiscal-year",
        required=True,
        type=int,
        help="Année fiscale du rapport annuel. Exemple : 2024",
    )

    parser.add_argument(
        "--official-domain",
        required=False,
        default=None,
        help="Domaine officiel de l'entreprise. Exemple : lvmh.com",
    )

    parser.add_argument(
        "--ticker",
        required=False,
        default=None,
        help="Ticker de l'entreprise. Exemple : MC",
    )

    parser.add_argument(
        "--isin",
        required=False,
        default=None,
        help="ISIN de l'entreprise. Exemple : FR0000121014",
    )

    parser.add_argument(
        "--jurisdiction",
        required=False,
        default=None,
        help="Pays ou juridiction. Exemple : France",
    )

    parser.add_argument(
        "--root-dir",
        required=False,
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

    retriever = AnnualReportRetriever(
        root_dir=Path(args.root_dir),
    )

    result = retriever.download_annual_report(
        company=company,
        fiscal_year=args.fiscal_year,
    )

    print("\n=== Annual Report Retriever Result ===")
    print(f"status: {result.status}")
    print(f"message: {result.message}")
    print(f"company_name: {result.company_name}")
    print(f"fiscal_year: {result.fiscal_year}")
    print(f"source_url: {result.source_url}")
    print(f"local_path: {result.local_path}")
    print(f"manifest_path: {result.manifest_path}")
    print(f"sha256: {result.sha256}")
    print(f"confidence_score: {result.confidence_score}")

    if result.best_candidate:
        print("\n=== Best Candidate ===")
        print(f"title: {result.best_candidate.title}")
        print(f"url: {result.best_candidate.url}")
        print(f"decision: {result.best_candidate.decision}")
        print(f"score: {result.best_candidate.score}")
        print(f"positive_signals: {result.best_candidate.positive_signals}")
        print(f"negative_signals: {result.best_candidate.negative_signals}")


if __name__ == "__main__":
    main()