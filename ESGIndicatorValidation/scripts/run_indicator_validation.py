#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "ESGIndicatorValidation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from esg_indicator_validation import IndicatorValidator


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = IndicatorValidator(Path(args.input_dir), Path(args.output_dir), overwrite=args.overwrite).run()
        print(json.dumps({
            "status": "success",
            "output_dir": str(result.output_dir),
            "validations_count": result.validations_count,
            "validation_status_distribution": result.summary.get("validation_status_distribution", {}),
            "validated_indicators_count": result.summary.get("validated_indicators_count", 0),
        }, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
