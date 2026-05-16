#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "ESGVisualExtraction" / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from esg_visual_extraction import ESGVisualExtractor


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run candidate-only visual extraction from ESGInformationExtraction outputs.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = ESGVisualExtractor(Path(args.input_dir), Path(args.output_dir), overwrite=args.overwrite).run()
        print(json.dumps({
            "status": "success",
            "output_dir": str(result.output_dir),
            "visual_candidates_count": result.candidates_count,
            "information_type_distribution": result.summary.get("information_type_distribution", {}),
            "ocr_status_distribution": result.summary.get("ocr_status_distribution", {}),
        }, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
