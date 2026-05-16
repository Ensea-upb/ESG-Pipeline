from __future__ import annotations
import argparse, json, sys, time
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.sbti_retriever.models import Company
from src.sbti_retriever.retriever import SBTiRetriever

DEFAULT_COMPANIES = [
    {"name": "LVMH", "official_domain": "lvmh.com", "ticker": "MC", "isin": "FR0000121014", "jurisdiction": "France"},
    {"name": "TotalEnergies", "official_domain": "totalenergies.com", "ticker": "TTE", "isin": "FR0000120271", "jurisdiction": "France"},
    {"name": "Schneider Electric", "official_domain": "se.com", "ticker": "SU", "isin": "FR0000121972", "jurisdiction": "France"},
]

def result_to_record(company, fiscal_year, result):
    return {"company_name": company.name, "official_domain": company.official_domain,
            "ticker": company.ticker, "isin": company.isin, "jurisdiction": company.jurisdiction,
            "fiscal_year": fiscal_year, "status": result.status, "message": result.message,
            "downloaded_count": result.downloaded_count, "failed_count": result.failed_count,
            "skipped_count": result.skipped_count, "downloaded": result.downloaded,
            "failed": result.failed, "skipped": result.skipped}

def print_record(record):
    print(f"\n{'='*70}\n  {record['company_name']} | FY{record['fiscal_year']}")
    print(f"  Status: {record['status']} | Downloaded: {record['downloaded_count']} | Failed: {record['failed_count']} | Skipped: {record['skipped_count']}")
    for item in record["downloaded"]:
        print(f"  + [{item['rank']}] score={item['score']} | {item['title'][:80]}")
    for item in record["failed"]:
        print(f"  x [{item['rank']}] {item['title'][:60]} | {item['download_status']}")

def print_summary(records, label):
    print(f"\n{'='*90}\nSYNTHESE DU BENCHMARK SBTI\n{'='*90}")
    header = f"{'Entreprise':<25} {'Status':<15} {'Downloaded':<12} {'Failed':<8} {'Skipped':<8}"
    print(header); print("-"*len(header))
    for r in records:
        print(f"{r['company_name'][:24]:<25} {str(r['status'])[:14]:<15} {str(r['downloaded_count']):<12} {str(r['failed_count']):<8} {str(r['skipped_count']):<8}")
    print("-"*len(header))
    print(f"Total downloaded : {sum(r['downloaded_count'] for r in records)}")
    print(f"Total failed     : {sum(r['failed_count'] for r in records)}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fiscal-year", type=int, default=2024)
    parser.add_argument("--root-dir", default="data/dossier_ingestion_0")
    parser.add_argument("--min-score", type=float, default=80.0)
    parser.add_argument("--sleep", type=float, default=1.0)
    args = parser.parse_args()

    root_dir = Path(args.root_dir)
    retriever = SBTiRetriever(root_dir=root_dir)
    records = []

    for company_config in DEFAULT_COMPANIES:
        company = Company(**company_config)
        print(f"\n{'#'*70}\n  {company.name} -- {args.fiscal_year}\n{'#'*70}")
        try:
            result = retriever.download_high_score_candidates(company=company, fiscal_year=args.fiscal_year, min_score=args.min_score)
            record = result_to_record(company=company, fiscal_year=args.fiscal_year, result=result)
        except Exception as exc:
            record = {"company_name": company.name, "official_domain": company.official_domain,
                      "ticker": company.ticker, "isin": company.isin, "jurisdiction": company.jurisdiction,
                      "fiscal_year": args.fiscal_year, "status": "exception", "message": str(exc),
                      "downloaded_count": 0, "failed_count": 0, "skipped_count": 0,
                      "downloaded": [], "failed": [], "skipped": []}
        records.append(record); print_record(record)
        if args.sleep > 0:
            time.sleep(args.sleep)

    print_summary(records, "SBTI")
    registry_dir = root_dir / "registry"; registry_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = "SBTI".lower().replace(" ", "_")
    output_path = registry_dir / f"benchmark_{safe_label}_{args.fiscal_year}_{timestamp}.json"
    output_path.write_text(json.dumps({"benchmark_name": f"SBTI_retriever_benchmark",
        "fiscal_year": args.fiscal_year, "created_at": datetime.now().isoformat(timespec="seconds"),
        "total_companies": len(records), "records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRapport JSON sauvegarde : {output_path}")

if __name__ == "__main__":
    main()
