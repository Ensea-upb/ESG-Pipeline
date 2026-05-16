from __future__ import annotations

import json
import sys
from pathlib import Path
from dataclasses import asdict, is_dataclass
from typing import Any

# Ajoute automatiquement la racine du projet au PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.document_postprocessing.registry_builder import DocumentRegistryBuilder
from src.document_postprocessing.scope import (
    get_input_root_from_env,
    get_output_dir_from_env,
    get_scope_from_env,
)


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
    builder = DocumentRegistryBuilder(
        project_root=PROJECT_ROOT,
        output_dir=get_output_dir_from_env(PROJECT_ROOT, "central_registry"),
        company_slugs=company_slugs,
        years=years,
        input_root=get_input_root_from_env(),
    )

    result = builder.build_registry()

    print("\n=== Document Registry Builder Result ===")
    print(f"status: {result.status}")
    print(f"message: {result.message}")
    print(f"total_manifests_found: {result.total_manifests_found}")
    print(f"total_documents_loaded: {result.total_documents_loaded}")
    print(f"total_errors: {result.total_errors}")
    print(f"output_json_path: {result.output_json_path}")
    print(f"output_csv_path: {result.output_csv_path}")

    if result.errors:
        print("\n--- Errors ---")
        for error in result.errors:
            print(json.dumps(error, ensure_ascii=False, indent=2))

    summary_path = get_output_dir_from_env(
        PROJECT_ROOT,
        "central_registry",
    ) / "registry_build_summary.json"

    summary_path.write_text(
        json.dumps(dataclass_to_dict(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nRésumé sauvegardé : {summary_path}")


if __name__ == "__main__":
    main()
