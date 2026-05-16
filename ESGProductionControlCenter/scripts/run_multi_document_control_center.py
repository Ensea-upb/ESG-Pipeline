from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ESGProductionControlCenter.src.esg_production_control_center.audit import write_batch_summary
from ESGProductionControlCenter.src.esg_production_control_center.output_discovery import discover_outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    outputs = [o for o in discover_outputs(".") if o["module_name"] == "ESGInformationExtraction"]
    rows = [{"document_id": o.get("document_id"), "input_dir": o["output_dir"], "status": "dry_run", "run_id": ""} for o in outputs]
    files = write_batch_summary(args.output_dir, rows, overwrite=args.overwrite)
    print(json.dumps({"status": "success", "documents_count": len(rows), "files_written": files}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
