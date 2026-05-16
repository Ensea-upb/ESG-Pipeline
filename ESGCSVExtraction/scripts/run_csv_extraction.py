#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "ESGCSVExtraction" / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from esg_csv_extraction import ESGCSVExtractor


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract candidate-only ESG CSV rows from documentary outputs.")
    parser.add_argument("--input-dir", required=True, help="Existing ESGInformationExtraction output directory.")
    parser.add_argument("--output-dir", required=True, help="Directory where CSV candidate outputs are written.")
    parser.add_argument("--overwrite", action="store_true", help="Replace expected output files if they already exist.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = ESGCSVExtractor(
            input_dir=Path(args.input_dir),
            output_dir=Path(args.output_dir),
            overwrite=args.overwrite,
        ).run()
        print(json.dumps({
            "status": "success",
            "output_dir": str(result.output_dir),
            "candidates_count": result.candidates_count,
            "information_type_distribution": result.summary.get("information_type_distribution", {}),
        }, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
