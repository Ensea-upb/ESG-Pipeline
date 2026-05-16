"""
benchmark_v1_vs_v2.py — Compare V1 and V2 extraction outputs.

Usage:
    python ESGVariableTargetedExtractionV2/scripts/benchmark_v1_vs_v2.py \\
        --v1-pilot-root "EXTERNAL_AUDIT_RUNS/strict_pilot_prepare_review_10docs_v2" \\
        --v2-output-root "ESGVariableTargetedExtractionV2/outputs/..." \\
        --manual-baseline "ESGVariableTargetedExtractionV2/benchmarks/schneider_tcfd_2023_manual_baseline_template.csv" \\
        --output-dir "ESGVariableTargetedExtractionV2/outputs/benchmark_v1_vs_v2"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.benchmark import run_benchmark


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Benchmark V1 vs V2 ESG extraction")
    p.add_argument("--v1-pilot-root", required=True, help="Path to V1 pilot run root")
    p.add_argument("--v2-output-root", required=True, help="Path to V2 outputs root")
    p.add_argument("--manual-baseline", default=None, help="Path to manual baseline CSV")
    p.add_argument("--output-dir", required=True, help="Output directory for benchmark results")
    return p.parse_args()


def main() -> dict:
    args = parse_args()

    print(f"[benchmark] V1 root: {args.v1_pilot_root}")
    print(f"[benchmark] V2 root: {args.v2_output_root}")
    print(f"[benchmark] Output : {args.output_dir}")

    result = run_benchmark(
        v1_pilot_root=args.v1_pilot_root,
        v2_output_root=args.v2_output_root,
        manual_baseline_path=args.manual_baseline,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, indent=2, default=str))
    return result


if __name__ == "__main__":
    main()
