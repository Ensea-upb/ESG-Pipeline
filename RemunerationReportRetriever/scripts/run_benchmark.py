from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.remuneration_report_retriever.models import Company
from src.remuneration_report_retriever.retriever import RemunerationReportRetriever


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
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, list):
        return [dataclass_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {key: dataclass_to_dict(value) for key, value in obj.items()}
    return obj


def result_to_record(company: Company, fiscal_year: int, result: Any) -> dict:
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
    print("\n" + "=" * 100)
    print("SYNTHÈSE DU BENCHMARK REMUNERATION REPORT")
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
        print(
            f"{record['company_name'][:24]:<25} "
            f"{str(record['status'])[:14]:<15} "
            f"{str(record['downloaded_count']):<12} "
            f"{str(record['failed_count']):<8} "
            f"{str(record['skipped_count']):<8}"
        )

    print("-" * len(header))
    print(f"Total downloaded : {sum(r['downloaded_count'] for r in records)}")
    print(f"Total failed     : {sum(r['failed_count'] for r in records)}")
    print(f"Total skipped    : {sum(r['skipped_count'] for r in records)}")


def save_benchmark_report(records: list[dict], root_dir: Path, fiscal_year: int) -> Path:
    registry_dir = root_dir / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = registry_dir / f"benchmark_remuneration_report_{fiscal_year}_{timestamp}.json"

    output_path.write_text(
        json.dumps(
            {
                "benchmark_name": "remuneration_report_retriever_benchmark",
                "fiscal_year": fiscal_year,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "total_companies": len(records),
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark du moteur RemunerationReportRetriever."
    )

    parser.add_argument("--fiscal-year", type=int, default=2024)
    parser.add_argument("--root-dir", default="data/dossier_ingestion_0")
    parser.add_argument("--min-score", type=float, default=80.0)
    parser.add_argument("--sleep", type=float, default=1.0)

    args = parser.parse_args()

    root_dir = Path(args.root_dir)
    retriever = RemunerationReportRetriever(root_dir=root_dir)

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
            record = result_to_record(company=company, fiscal_year=args.fiscal_year, result=result)

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
        records=records, root_dir=root_dir, fiscal_year=args.fiscal_year
    )
    print(f"\nRapport JSON sauvegardé : {output_path}")


if __name__ == "__main__":
    main()
