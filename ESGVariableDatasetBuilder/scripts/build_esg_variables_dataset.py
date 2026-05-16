from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.dataset_builder import build_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the ESG variables company-year dataset from corpus-derived preparation outputs.")
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--company")
    parser.add_argument("--year")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--override-empty-company-from-cli",
        action="store_true",
        help="Fill empty company fields with --company value. Only allowed in single-document mode.",
    )
    parser.add_argument(
        "--override-empty-year-from-cli",
        action="store_true",
        help="Fill empty fiscal_year fields with --year value. Only allowed in single-document mode.",
    )
    parser.add_argument(
        "--single-document-mode",
        action="store_true",
        help="Assert that all loaded records share a single document_id. Required for override flags with multi-doc inputs.",
    )
    args = parser.parse_args()
    build_dataset(
        Path(args.input_root),
        Path(args.output_dir),
        company=args.company,
        year=args.year,
        overwrite=args.overwrite,
        override_empty_company_from_cli=bool(args.override_empty_company_from_cli),
        override_empty_year_from_cli=bool(args.override_empty_year_from_cli),
        single_document_mode=bool(args.single_document_mode),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
