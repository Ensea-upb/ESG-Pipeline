from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.document_postprocessing.taxonomy_corpus_organizer import (
    TaxonomyCorpusOrganizer,
)
from src.document_postprocessing.scope import (
    get_corpus_root_from_env,
    get_output_dir_from_env,
    get_scope_from_env,
)


def main() -> None:
    company_slugs, years = get_scope_from_env()
    organizer = TaxonomyCorpusOrganizer(
        organized_index_csv_path=get_output_dir_from_env(
            PROJECT_ROOT,
            "organized_corpus",
        )
        / "organized_documents_index.csv",
        output_corpus_root=get_corpus_root_from_env(
            "ESG_POSTPROCESS_ESG_CORPUS_TAXONOMY_ROOT",
            WORKSPACE_ROOT / "ESGCorpusTaxonomy",
        ),
        output_dir=get_output_dir_from_env(PROJECT_ROOT, "organized_corpus_taxonomy"),
        company_slugs=company_slugs,
        years=years,
    )

    result = organizer.organize()

    print("\n=== Taxonomy Corpus Organizer Result ===")
    print(f"status: {result.status}")
    print(f"message: {result.message}")
    print(f"total_documents_processed: {result.total_documents_processed}")
    print(f"total_copied_files: {result.total_copied_files}")
    print(f"total_existing_files: {result.total_existing_files}")
    print(f"total_missing_files: {result.total_missing_files}")
    print(f"total_needs_review: {result.total_needs_review}")
    print(f"total_errors: {result.total_errors}")
    print(f"output_corpus_root: {result.output_corpus_root}")
    print(f"output_index_csv_path: {result.output_index_csv_path}")
    print(f"output_index_json_path: {result.output_index_json_path}")
    print(f"summary_path: {result.summary_path}")

    print("\n--- Distribution by official_doc_type ---")
    for doc_type, count in result.distribution_by_official_doc_type.items():
        print(f"{doc_type}: {count}")

    if result.errors:
        print("\n--- Errors ---")
        for error in result.errors:
            print(json.dumps(error, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
