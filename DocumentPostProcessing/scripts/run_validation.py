from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.document_postprocessing.validator import DocumentValidator
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
    validator = DocumentValidator(
        organized_index_csv_path=get_output_dir_from_env(
            PROJECT_ROOT,
            "organized_corpus",
        )
        / "organized_documents_index.csv",
        output_dir=get_output_dir_from_env(PROJECT_ROOT, "validation"),
        company_slugs=company_slugs,
        years=years,
    )

    result = validator.validate()

    print("\n=== Document Validation Result ===")
    print(f"status: {result.status}")
    print(f"message: {result.message}")
    print(f"total_documents: {result.total_documents}")
    print(f"total_valid_pdf: {result.total_valid_pdf}")
    print(f"total_missing_file: {result.total_missing_file}")
    print(f"total_not_pdf: {result.total_not_pdf}")
    print(f"total_unreadable_pdf: {result.total_unreadable_pdf}")
    print(f"total_likely_valid: {result.total_likely_valid}")
    print(f"total_needs_review: {result.total_needs_review}")
    print(f"total_likely_wrong_company: {result.total_likely_wrong_company}")
    print(f"total_unreadable: {result.total_unreadable}")
    print(f"total_errors: {result.total_errors}")
    print(f"output_json_path: {result.output_json_path}")
    print(f"output_csv_path: {result.output_csv_path}")
    print(f"summary_path: {result.summary_path}")

    if result.errors:
        print("\n--- Errors ---")
        for error in result.errors:
            print(json.dumps(error, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
