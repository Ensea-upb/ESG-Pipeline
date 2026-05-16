from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from dataclasses import asdict, is_dataclass
from typing import Any


def configure_text_output() -> None:
    """
    Evite qu'un print contenant des caracteres Unicode fasse planter le script
    sur des consoles Windows configurees en encodage local.
    """

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


configure_text_output()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.corporate_policy_retriever.models import Company, PolicyType
from src.corporate_policy_retriever.retriever import CorporatePolicyRetriever


def dataclass_to_dict(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, list):
        return [dataclass_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {key: dataclass_to_dict(value) for key, value in obj.items()}
    return obj


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Telecharger toutes les politiques corporates dont le score depasse un seuil."
    )

    parser.add_argument("--company-name", required=True, help="Nom de l'entreprise.")
    parser.add_argument("--reference-year", required=True, type=int, help="Annee de reference.")
    parser.add_argument(
        "--policy-type",
        required=True,
        choices=[pt.value for pt in PolicyType],
        help="Type de politique a telecharger.",
    )
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
    policy_type = PolicyType(args.policy_type)

    retriever = CorporatePolicyRetriever(root_dir=Path(args.root_dir))

    result = retriever.download_high_score_candidates(
        company=company,
        policy_type=policy_type,
        reference_year=args.reference_year,
        min_score=args.min_score,
    )

    print(f"\n=== CorporatePolicyRetriever Result ({policy_type.value}) ===")
    print(f"status: {result.status}")
    print(f"message: {result.message}")
    print(f"company_name: {result.company_name}")
    print(f"reference_year: {result.reference_year}")
    print(f"policy_type: {result.policy_type}")
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
    output_path = (
        output_dir
        / f"download_all_policy_{policy_type.value}_{safe_name}_{args.reference_year}.json"
    )

    output_path.write_text(
        json.dumps(
            {
                "company": asdict(company),
                "reference_year": args.reference_year,
                "policy_type": policy_type.value,
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
