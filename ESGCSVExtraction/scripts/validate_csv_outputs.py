#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "ESGCSVExtraction" / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from esg_csv_extraction.contract import default_contract_path
from esg_csv_extraction.validators import print_json, validate_csv_outputs


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ESGCSVExtraction outputs against the CSV contract.")
    parser.add_argument("--output-dir", required=True, help="Directory containing ESGCSVExtraction CSV outputs.")
    parser.add_argument("--contract-path", default=str(default_contract_path()), help="CSV output contract JSON path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = validate_csv_outputs(Path(args.output_dir), Path(args.contract_path))
    print_json(result)
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
