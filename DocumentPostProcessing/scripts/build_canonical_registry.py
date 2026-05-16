from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.document_postprocessing.canonical_registry import CanonicalRegistryBuilder
from src.document_postprocessing.scope import get_output_dir_from_env, get_scope_from_env


def dataclass_to_dict(obj: Any) -> Any:
    """
    Convertit recursivement les dataclasses en dictionnaires.
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

    builder = CanonicalRegistryBuilder(
        registry_csv_path=registry_csv_path,
        output_dir=output_dir,
        company_slugs=company_slugs,
        years=years,
    )

    result = builder.build()

    print("\n=== Canonical Registry Builder Result ===")
    print(f"status: {result.status}")
    print(f"message: {result.message}")
    print(f"total_input_documents: {result.total_input_documents}")
    print(f"total_documents_with_sha256: {result.total_documents_with_sha256}")
    print(f"total_unique_documents: {result.total_unique_documents}")
    print(f"total_duplicate_groups: {result.total_duplicate_groups}")
    print(f"total_duplicate_documents: {result.total_duplicate_documents}")
    print(f"total_multi_family_groups: {result.total_multi_family_groups}")
    print(f"output_json_path: {result.output_json_path}")
    print(f"output_csv_path: {result.output_csv_path}")
    print(f"summary_path: {result.summary_path}")

    if result.errors:
        print("\n--- Errors ---")
        for error in result.errors:
            print(json.dumps(error, ensure_ascii=False, indent=2))

    print(f"\nResume sauvegarde : {result.summary_path}")


if __name__ == "__main__":
    main()
