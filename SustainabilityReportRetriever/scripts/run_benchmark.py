from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Ajoute automatiquement la racine du projet au PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.sustainability_report_retriever.models import Company
from src.sustainability_report_retriever.retriever import SustainabilityReportRetriever


DEFAULT_COMPANIES = [
    {
        "name": "LVMH",
        "official_domain": "lvmh.com",
        "ticker": "MC",
        "isin": "FR0000121014",
        "jurisdiction": "France",
    },
    {
        "name": "TotalEnergies",
        "official_domain": "totalenergies.com",
        "ticker": "TTE",
        "isin": "FR0000120271",
        "jurisdiction": "France",
    },
    {
        "name": "Schneider Electric",
        "official_domain": "se.com",
        "ticker": "SU",
        "isin": "FR0000121972",
        "jurisdiction": "France",
    },
]


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


def result_to_record(company: Company, fiscal_year: int, result: Any) -> dict:
    """
    Convertit un DownloadResult en dictionnaire exploitable.
    """

    return {
        "company_name": company.name,
        "official_domain": company.official_domain,
        "ticker": company.ticker,
        "isin": company.isin,
        "jurisdiction": company.jurisdiction,
        "fiscal_year": fiscal_year,
        "status": result.status,
        "message": result.message,
        "downloaded_count": result.downloaded_count,
        "failed_count": result.failed_count,
        "skipped_count": result.skipped_count,
        "downloaded": result.downloaded,
        "failed": result.failed,
        "skipped": result.skipped,
    }


def print_record(record: dict) -> None:
    """
    Affiche le détail d’un résultat individuel.
    """

    print("\n" + "=" * 80)
    print(f"Entreprise      : {record['company_name']}")
    print(f"Année fiscale   : {record['fiscal_year']}")
    print(f"Status          : {record['status']}")
    print(f"Downloaded      : {record['downloaded_count']}")
    print(f"Failed          : {record['failed_count']}")
    print(f"Skipped         : {record['skipped_count']}")

    if record["downloaded"]:
        print("\nDocuments téléchargés:")
        for item in record["downloaded"]:
            print(f"  - [{item['rank']}] score={item['score']} | {item['title']}")

    if record["failed"]:
        print("\nÉchecs:")
        for item in record["failed"]:
            print(
                f"  - [{item['rank']}] score={item['score']} | "
                f"{item['title']} | {item['download_status']}"
            )

    if record["skipped"]:
        print("\nIgnorés:")
        for item in record["skipped"]:
            print(
                f"  - [{item['rank']}] score={item['score']} | "
                f"{item['title']} | {item['decision']}"
            )


def print_summary(records: list[dict]) -> None:
    """
    Affiche une synthèse compacte.
    """

    print("\n" + "=" * 100)
    print("SYNTHÈSE DU BENCHMARK SUSTAINABILITY")
    print("=" * 100)

    header = (
        f"{'Entreprise':<25} "
        f"{'Status':<15} "
        f"{'Downloaded':<12} "
        f"{'Failed':<8} "
        f"{'Skipped':<8}"
    )
    print(header)
    print("-" * len(header))

    for record in records:
        company = record["company_name"][:24]
        status = str(record["status"])[:14]
        downloaded = str(record["downloaded_count"])
        failed = str(record["failed_count"])
        skipped = str(record["skipped_count"])

        print(
            f"{company:<25} "
            f"{status:<15} "
            f"{downloaded:<12} "
            f"{failed:<8} "
            f"{skipped:<8}"
        )

    print("-" * len(header))

    total_downloaded = sum(r["downloaded_count"] for r in records)
    total_failed = sum(r["failed_count"] for r in records)
    total_skipped = sum(r["skipped_count"] for r in records)

    print(f"Total downloaded : {total_downloaded}")
    print(f"Total failed     : {total_failed}")
    print(f"Total skipped    : {total_skipped}")


def save_benchmark_report(
    records: list[dict],
    root_dir: Path,
    fiscal_year: int,
) -> Path:
    """
    Sauvegarde le rapport de benchmark en JSON.
    """

    registry_dir = root_dir / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_path = (
        registry_dir
        / f"benchmark_sustainability_report_{fiscal_year}_{timestamp}.json"
    )

    payload = {
        "benchmark_name": "sustainability_report_retriever_benchmark",
        "fiscal_year": fiscal_year,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "total_companies": len(records),
        "records": records,
    }

    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark du moteur SustainabilityReportRetriever."
    )

    parser.add_argument(
        "--fiscal-year",
        type=int,
        default=2024,
        help="Année fiscale à tester. Défaut : 2024.",
    )

    parser.add_argument(
        "--root-dir",
        default="data/dossier_ingestion_0",
        help="Dossier racine de stockage.",
    )

    parser.add_argument(
        "--min-score",
        type=float,
        default=80.0,
        help="Score minimal de téléchargement.",
    )

    parser.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="Pause en secondes entre deux entreprises.",
    )

    args = parser.parse_args()

    root_dir = Path(args.root_dir)

    retriever = SustainabilityReportRetriever(
        root_dir=root_dir,
    )

    records: list[dict] = []

    for company_config in DEFAULT_COMPANIES:
        company = Company(**company_config)

        print("\n" + "#" * 80)
        print(f"Traitement : {company.name} — {args.fiscal_year}")
        print("#" * 80)

        try:
            result = retriever.download_high_score_candidates(
                company=company,
                fiscal_year=args.fiscal_year,
                min_score=args.min_score,
            )

            record = result_to_record(
                company=company,
                fiscal_year=args.fiscal_year,
                result=result,
            )

        except Exception as exc:
            record = {
                "company_name": company.name,
                "official_domain": company.official_domain,
                "ticker": company.ticker,
                "isin": company.isin,
                "jurisdiction": company.jurisdiction,
                "fiscal_year": args.fiscal_year,
                "status": "exception",
                "message": str(exc),
                "downloaded_count": 0,
                "failed_count": 0,
                "skipped_count": 0,
                "downloaded": [],
                "failed": [],
                "skipped": [],
            }

        records.append(record)
        print_record(record)

        if args.sleep > 0:
            time.sleep(args.sleep)

    print_summary(records)

    output_path = save_benchmark_report(
        records=records,
        root_dir=root_dir,
        fiscal_year=args.fiscal_year,
    )

    print(f"\nRapport JSON sauvegardé : {output_path}")


if __name__ == "__main__":
    main()