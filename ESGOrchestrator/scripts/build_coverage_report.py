from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd


def resolve_project_root() -> Path:
    env_root = os.getenv("ESG_PROJECT_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve() / "ESGOrchestrator"
    return Path(__file__).resolve().parents[1]


PROJECT_ROOT = resolve_project_root()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a simple coverage summary.")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    run_dir = PROJECT_ROOT / "runs" / args.run_id
    matrix_path = run_dir / "coverage_matrix.csv"
    if not matrix_path.exists():
        raise FileNotFoundError(f"Coverage matrix not found: {matrix_path}")

    df = pd.read_csv(matrix_path)
    summary = {
        "run_id": args.run_id,
        "total_tasks": len(df),
        "status_counts": df["status"].value_counts().to_dict(),
        "companies": sorted(df["company_slug"].dropna().unique().tolist()),
        "years": sorted(int(year) for year in df["fiscal_year"].dropna().unique()),
    }
    output_path = run_dir / "coverage_report.json"
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Coverage report written: {output_path}")


if __name__ == "__main__":
    main()
