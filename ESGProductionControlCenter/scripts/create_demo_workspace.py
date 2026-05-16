from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ESGProductionControlCenter.src.esg_production_control_center.demo_data import create_demo_workspace, write_demo_business_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default="ESGProductionControlCenter/outputs/demo")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    result = create_demo_workspace(args.output_root, overwrite=args.overwrite)
    result["report_files"] = write_demo_business_report(result["demo_dir"])
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
