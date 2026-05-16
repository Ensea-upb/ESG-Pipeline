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

from src.corporate_policy_retriever.models import Company, PolicyType
from src.corporate_policy_retriever.retriever import CorporatePolicyRetriever


DEFAULT_COMPANIES = [
    {"name": "LVMH", "official_domain": "lvmh.com", "ticker": "MC", "isin": "FR0000121014", "jurisdiction": "France"},
    {"name": "TotalEnergies", "official_domain": "totalenergies.com", "ticker": "TTE", "isin": "FR0000120271", "jurisdiction": "France"},
    {"name": "Schneider Electric", "official_domain": "se.com", "ticker": "SU", "isin": "FR0000121972", "jurisdiction": "France"},
]

ALL_POLICY_TYPES = list(PolicyType)


def dataclass_to_dict(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, list):
        return [dataclass_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {key: dataclass_to_dict(value) for key, value in obj.items()}
    return obj


def print_record(record: dict) -> None:
    print(f"\n{'='*70}")
    print(f"  {record['company_name']} | {record['policy_type']}")
    print(f"  Status: {record['status']} | Downloaded: {record['downloaded_count']} "
          f"| Failed: {record['failed_count']} | Skipped: {record['skipped_count']}")
    if record["downloaded"]:
        for item in record["downloaded"]:
            print(f"  OK [{item['rank']}] score={item['score']} | {item['title'][:80]}")
    if record["failed"]:
        for item in record["failed"]:
            print(f"  !! [{item['rank']}] {item['title'][:60]} | {item['download_status']}")


def print_summary(records: list[dict]) -> None:
    print("\n" + "=" * 100)
    print("SYNTHESE DU BENCHMARK CORPORATE POLICY")
    print("=" * 100)
    header = f"{'Entreprise':<22} {'Type politique':<25} {'Downloaded':<12} {'Failed':<8} {'Skipped':<8}"
    print(header)
    print("-" * len(header))
    for record in records:
        print(f"{record['company_name'][:21]:<22} {record['policy_type'][:24]:<25} "
              f"{str(record['downloaded_count']):<12} {str(record['failed_count']):<8} "
              f"{str(record['skipped_count']):<8}")
    print("-" * len(header))
    print(f"Total downloaded : {sum(r['downloaded_count'] for r in records)}")
    print(f"Total failed     : {sum(r['failed_count'] for r in records)}")
    print(f"Total skipped    : {sum(r['skipped_count'] for r in records)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark du moteur CorporatePolicyRetriever.")
    parser.add_argument("--reference-year", type=int, default=2024)
    parser.add_argument("--root-dir", default="data/dossier_ingestion_0")
    parser.add_argument("--min-score", type=float, default=80.0)
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument(
        "--policy-types",
        nargs="+",
        default=[pt.value for pt in ALL_POLICY_TYPES],
        help="Types de politiques à tester (défaut : tous).",
    )
    args = parser.parse_args()

    policy_types = [PolicyType(pt) for pt in args.policy_types]
    root_dir = Path(args.root_dir)
    retriever = CorporatePolicyRetriever(root_dir=root_dir)
    records: list[dict] = []

    for company_config in DEFAULT_COMPANIES:
        company = Company(**company_config)
        for policy_type in policy_types:
            print(f"\n{'#'*70}")
            print(f"  {company.name} | {policy_type.value} | {args.reference_year}")
            print(f"{'#'*70}")

            try:
                result = retriever.download_high_score_candidates(
                    company=company, policy_type=policy_type,
                    reference_year=args.reference_year, min_score=args.min_score,
                )
                record = {
                    "company_name": company.name, "policy_type": policy_type.value,
                    "reference_year": args.reference_year,
                    "status": result.status, "message": result.message,
                    "downloaded_count": result.downloaded_count,
                    "failed_count": result.failed_count, "skipped_count": result.skipped_count,
                    "downloaded": result.downloaded, "failed": result.failed, "skipped": result.skipped,
                }
            except Exception as exc:
                record = {
                    "company_name": company.name, "policy_type": policy_type.value,
                    "reference_year": args.reference_year, "status": "exception",
                    "message": str(exc), "downloaded_count": 0,
                    "failed_count": 0, "skipped_count": 0,
                    "downloaded": [], "failed": [], "skipped": [],
                }

            records.append(record)
            print_record(record)
            if args.sleep > 0:
                time.sleep(args.sleep)

    print_summary(records)

    registry_dir = root_dir / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = registry_dir / f"benchmark_corporate_policy_{args.reference_year}_{timestamp}.json"
    output_path.write_text(json.dumps({
        "benchmark_name": "corporate_policy_retriever_benchmark",
        "reference_year": args.reference_year,
        "policy_types_tested": [pt.value for pt in policy_types],
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "total_records": len(records), "records": records,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRapport JSON sauvegardé : {output_path}")


if __name__ == "__main__":
    main()
