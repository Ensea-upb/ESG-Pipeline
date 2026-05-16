from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.document_postprocessing.corpus_organizer import CorpusOrganizer
from src.document_postprocessing.scope import (
    get_corpus_root_from_env,
    get_output_dir_from_env,
    get_scope_from_env,
)


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
    organizer = CorpusOrganizer(
        canonical_csv_path=get_output_dir_from_env(PROJECT_ROOT, "deduplication")
        / "canonical_documents.csv",
        output_corpus_root=get_corpus_root_from_env(
            "ESG_POSTPROCESS_ESG_CORPUS_ROOT",
            WORKSPACE_ROOT / "ESGCorpus",
        ),
        output_dir=get_output_dir_from_env(PROJECT_ROOT, "organized_corpus"),
        company_slugs=company_slugs,
        years=years,
    )

    result = organizer.organize()

    print("\n=== Corpus Organizer Result ===")
    print(f"status: {result.status}")
    print(f"message: {result.message}")
    print(f"total_canonical_documents: {result.total_canonical_documents}")
    print(
        "total_document_family_copies_planned: "
        f"{result.total_document_family_copies_planned}"
    )
    print(f"total_copied_files: {result.total_copied_files}")
    print(f"total_existing_files: {result.total_existing_files}")
    print(f"total_missing_files: {result.total_missing_files}")
    print(f"total_errors: {result.total_errors}")
    print(f"output_corpus_root: {result.output_corpus_root}")
    print(f"output_index_csv_path: {result.output_index_csv_path}")
    print(f"output_index_json_path: {result.output_index_json_path}")
    print(f"summary_path: {result.summary_path}")

    if result.errors:
        print("\n--- Errors ---")
        for error in result.errors:
            print(json.dumps(error, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
