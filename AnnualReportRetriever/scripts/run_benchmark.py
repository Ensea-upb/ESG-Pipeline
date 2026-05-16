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

from src.annual_report_retriever.models import Company
from src.annual_report_retriever.retriever import AnnualReportRetriever


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
        "name": "Air Liquide",
        "official_domain": "airliquide.com",
        "ticker": "AI",
        "isin": "FR0000120073",
        "jurisdiction": "France",
    },
    {
        "name": "BNP Paribas",
        "official_domain": "bnpparibas.com",
        "ticker": "BNP",
        "isin": "FR0000131104",
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

    best_candidate = result.best_candidate

    return {
        "company_name": company.name,
        "official_domain": company.official_domain,
        "ticker": company.ticker,
        "isin": company.isin,
        "jurisdiction": company.jurisdiction,
        "fiscal_year": fiscal_year,
        "status": result.status,
        "message": result.message,
        "source_url": result.source_url,
        "local_path": result.local_path,
        "manifest_path": result.manifest_path,
        "sha256": result.sha256,
        "confidence_score": result.confidence_score,
        "best_candidate_title": best_candidate.title if best_candidate else None,
        "best_candidate_url": best_candidate.url if best_candidate else None,
        "best_candidate_decision": best_candidate.decision if best_candidate else None,
        "best_candidate_score": best_candidate.score if best_candidate else None,
        "positive_signals": best_candidate.positive_signals if best_candidate else [],
        "negative_signals": best_candidate.negative_signals if best_candidate else [],
    }


def print_record(record: dict) -> None:
    """
    Affiche un résultat individuel.
    """

    print("\n" + "=" * 80)
    print(f"Entreprise      : {record['company_name']}")
    print(f"Année fiscale   : {record['fiscal_year']}")
    print(f"Status          : {record['status']}")
    print(f"Score           : {record['confidence_score']}")
    print(f"Décision        : {record['best_candidate_decision']}")
    print(f"Titre candidat  : {record['best_candidate_title']}")
    print(f"URL source      : {record['source_url']}")
    print(f"Chemin local    : {record['local_path']}")
    print(f"Manifest        : {record['manifest_path']}")

    if record["negative_signals"]:
        print("Signaux négatifs:")
        for signal in record["negative_signals"]:
            print(f"  - {signal}")


def print_summary(records: list[dict]) -> None:
    """
    Affiche un tableau de synthèse simple sans dépendance externe.
    """

    print("\n" + "=" * 100)
    print("SYNTHÈSE DU BENCHMARK")
    print("=" * 100)

    header = f"{'Entreprise':<25} {'Status':<25} {'Score':<8} {'Décision':<25}"
    print(header)
    print("-" * len(header))

    for record in records:
        company = record["company_name"][:24]
        status = str(record["status"])[:24]
        score = str(record["confidence_score"])
        decision = str(record["best_candidate_decision"])[:24]

        print(f"{company:<25} {status:<25} {score:<8} {decision:<25}")

    success_count = sum(1 for r in records if r["status"] == "success")
    total = len(records)

    print("-" * len(header))
    print(f"Succès : {success_count}/{total}")


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

    output_path = registry_dir / f"benchmark_annual_report_{fiscal_year}_{timestamp}.json"

    payload = {
        "benchmark_name": "annual_report_retriever_benchmark",
        "fiscal_year": fiscal_year,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "total_companies": len(records),
        "success_count": sum(1 for r in records if r["status"] == "success"),
        "records": records,
    }

    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark du moteur AnnualReportRetriever."
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
        "--sleep",
        type=float,
        default=1.0,
        help="Pause en secondes entre deux entreprises pour éviter les appels trop rapides.",
    )

    args = parser.parse_args()

    root_dir = Path(args.root_dir)

    retriever = AnnualReportRetriever(
        root_dir=root_dir,
    )

    records: list[dict] = []

    for company_config in DEFAULT_COMPANIES:
        company = Company(**company_config)

        print("\n" + "#" * 80)
        print(f"Traitement : {company.name} — {args.fiscal_year}")
        print("#" * 80)

        try:
            result = retriever.download_annual_report(
                company=company,
                fiscal_year=args.fiscal_year,
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
                "source_url": None,
                "local_path": None,
                "manifest_path": None,
                "sha256": None,
                "confidence_score": None,
                "best_candidate_title": None,
                "best_candidate_url": None,
                "best_candidate_decision": None,
                "best_candidate_score": None,
                "positive_signals": [],
                "negative_signals": [],
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