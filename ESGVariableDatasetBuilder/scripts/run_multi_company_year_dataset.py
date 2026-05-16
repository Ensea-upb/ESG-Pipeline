from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.multi_company_year import build_multi_company_year_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a global ESG variables dataset across discovered company-years.")
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    build_multi_company_year_dataset(Path(args.input_root), Path(args.output_dir), overwrite=args.overwrite)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
