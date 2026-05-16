from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ESGProductionControlCenter.src.esg_production_control_center.validators import validate_control_center_output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--contract-path", required=False)
    args = parser.parse_args()
    result = validate_control_center_output(args.output_dir, args.contract_path)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
