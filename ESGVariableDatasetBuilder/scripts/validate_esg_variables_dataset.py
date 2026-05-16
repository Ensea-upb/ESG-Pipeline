from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.config import DEFAULT_DICTIONARY_PATH
from ESGVariableDatasetBuilder.src.esg_variable_dataset_builder.validators import validate_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ESGVariableDatasetBuilder outputs against the v0 contract.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--contract-path", required=True)
    args = parser.parse_args()
    result = validate_dataset(Path(args.output_dir), Path(args.contract_path), DEFAULT_DICTIONARY_PATH)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
