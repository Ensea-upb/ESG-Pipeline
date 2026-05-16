from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

# Ajoute automatiquement la racine du projet au PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.document_postprocessing.deduplicator import DocumentDeduplicator
from src.document_postprocessing.scope import get_output_dir_from_env, get_scope_from_env


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
    company_slugs, years = get_scope_from_env()
    registry_csv_path = (
        get_output_dir_from_env(PROJECT_ROOT, "central_registry")
        / "documents_registry.csv"
    )
    output_dir = get_output_dir_from_env(PROJECT_ROOT, "deduplication")

    deduplicator = DocumentDeduplicator(
        registry_csv_path=registry_csv_path,
        output_dir=output_dir,
        company_slugs=company_slugs,
        years=years,
    )

    result = deduplicator.run_exact_deduplication()

    print("\n=== Document Deduplication Result ===")
    print(f"status: {result.status}")
    print(f"message: {result.message}")
    print(f"total_documents: {result.total_documents}")
    print(f"total_documents_with_sha256: {result.total_documents_with_sha256}")
    print(f"total_unique_sha256: {result.total_unique_sha256}")
    print(f"total_duplicate_groups: {result.total_duplicate_groups}")
    print(f"total_duplicate_documents: {result.total_duplicate_documents}")
    print(f"output_json_path: {result.output_json_path}")
    print(f"output_csv_path: {result.output_csv_path}")
    print(f"summary_path: {result.summary_path}")

    run_summary_path = output_dir / "run_deduplication_summary.json"

    run_summary_path.write_text(
        json.dumps(dataclass_to_dict(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nRésumé d'exécution sauvegardé : {run_summary_path}")


if __name__ == "__main__":
    main()
