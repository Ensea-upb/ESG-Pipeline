from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.document_postprocessing.document_selector import DocumentSelector
from src.document_postprocessing.scope import (
    get_corpus_root_from_env,
    get_output_dir_from_env,
    get_scope_from_env,
)


def main() -> None:
    company_slugs, years = get_scope_from_env()
    selector = DocumentSelector(
        taxonomy_index_csv_path=get_output_dir_from_env(
            PROJECT_ROOT,
            "organized_corpus_taxonomy",
        )
        / "taxonomy_organized_documents_index.csv",
        validation_results_csv_path=get_output_dir_from_env(
            PROJECT_ROOT,
            "validation",
        )
        / "document_validation_results.csv",
        output_final_corpus_root=get_corpus_root_from_env(
            "ESG_POSTPROCESS_ESG_FINAL_CORPUS_ROOT",
            WORKSPACE_ROOT / "ESGFinalCorpus",
        ),
        output_dir=get_output_dir_from_env(PROJECT_ROOT, "selection"),
        company_slugs=company_slugs,
        years=years,
    )

    result = selector.select()

    print("\n=== Final Document Selection Result ===")
    print(f"status: {result.status}")
    print(f"message: {result.message}")
    print(f"total_batches: {result.total_batches}")
    print(f"total_input_documents: {result.total_input_documents}")
    print(f"total_selected_documents: {result.total_selected_documents}")
    print(f"total_rejected_documents: {result.total_rejected_documents}")
    print(f"total_selected_needs_review: {result.total_selected_needs_review}")
    print(f"total_redundant_same_hash: {result.total_redundant_same_hash}")
    print(f"total_integrated_in_urd: {result.total_integrated_in_urd}")
    print(
        "total_superseded_by_csrd_statement: "
        f"{result.total_superseded_by_csrd_statement}"
    )
    print(f"total_likely_wrong_company: {result.total_likely_wrong_company}")
    print(f"total_errors: {result.total_errors}")
    print(f"output_final_corpus_root: {result.output_final_corpus_root}")
    print(f"selected_csv_path: {result.selected_csv_path}")
    print(f"selected_json_path: {result.selected_json_path}")
    print(f"rejected_csv_path: {result.rejected_csv_path}")
    print(f"summary_path: {result.summary_path}")

    if result.errors:
        print("\n--- Errors ---")
        for error in result.errors:
            print(json.dumps(error, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
