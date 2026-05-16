"""
benchmark.py — V1 vs V2 comparison. Read-only on all source directories.
Never modifies V1 pilot outputs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_csv, read_json, write_csv, write_json

_V1_WORKSPACE_SENTINEL = "manual_review_workspace.csv"
_V2_CANDIDATES_FILE = "targeted_candidates_v2.csv"

_ALL_VARIABLES = [
    "co2_emissions", "carbon_intensity", "energy_consumption", "water_consumption",
    "waste", "biodiversity", "fossil_exposure",
    "turnover", "diversity", "work_accidents", "human_capital", "supply_chain", "human_rights",
    "board_independence", "ceo_chairman_separation", "remuneration",
    "shareholder_rights", "transparency",
    "esg_scandals", "fraud", "corruption", "pollution", "lawsuits", "social_controversies",
    "market_cap", "volatility", "leverage", "roa", "roe", "liquidity", "stock_returns",
]


def _find_v1_workspaces(v1_pilot_root: Path) -> list[dict[str, Any]]:
    workspaces: list[dict[str, Any]] = []
    if not v1_pilot_root.exists():
        return workspaces
    for company_dir in sorted(v1_pilot_root.iterdir()):
        if not company_dir.is_dir():
            continue
        for year_dir in sorted(company_dir.iterdir()):
            if not year_dir.is_dir():
                continue
            for doc_type_dir in sorted(year_dir.iterdir()):
                if not doc_type_dir.is_dir():
                    continue
                for canonical_dir in sorted(doc_type_dir.iterdir()):
                    if not canonical_dir.is_dir() or not canonical_dir.name.startswith("canonical_"):
                        continue
                    ws_path = canonical_dir / "04_review_workspace" / _V1_WORKSPACE_SENTINEL
                    if ws_path.exists():
                        workspaces.append({
                            "company": company_dir.name,
                            "year": year_dir.name,
                            "doc_type": doc_type_dir.name,
                            "canonical_id": canonical_dir.name,
                            "workspace_path": str(ws_path),
                            "workspace_dir": str(canonical_dir / "04_review_workspace"),
                        })
    return workspaces


def _find_v2_outputs(v2_output_root: Path) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    if not v2_output_root.exists():
        return outputs
    for cand_file in sorted(v2_output_root.rglob(_V2_CANDIDATES_FILE)):
        outputs.append({
            "output_dir": str(cand_file.parent),
            "candidates_path": str(cand_file),
        })
    return outputs


def _load_v1_stats(workspace_path: str) -> dict[str, Any]:
    records = read_csv(workspace_path)
    if not records:
        return {"total": 0, "possible_indicator": 0, "needs_review": 0,
                "reject_candidate": 0, "families": {}}
    total = len(records)
    counts: dict[str, int] = {}
    families: dict[str, int] = {}
    for r in records:
        s = r.get("validation_status", r.get("candidate_status", "unknown"))
        counts[s] = counts.get(s, 0) + 1
        fam = r.get("indicator_family", "unknown")
        families[fam] = families.get(fam, 0) + 1
    return {
        "total": total,
        "possible_indicator": counts.get("possible_indicator", 0),
        "needs_review": counts.get("needs_review", 0),
        "reject_candidate": counts.get("reject_candidate", 0),
        "families": families,
        "missing_value_count": sum(
            1 for r in records if not r.get("raw_value", "").strip()
        ),
        "missing_quote_count": sum(
            1 for r in records if not r.get("quote", "").strip()
        ),
    }


def _load_v2_stats(candidates_path: str) -> dict[str, Any]:
    records = read_csv(candidates_path)
    if not records:
        return {"total": 0, "candidate_found": 0, "needs_review": 0,
                "rejected": 0, "variables_covered": []}
    total = len(records)
    found = sum(1 for r in records if r.get("candidate_status") == "candidate_found")
    nr = sum(1 for r in records if r.get("candidate_status") == "needs_review")
    rejected = sum(1 for r in records if str(r.get("candidate_status", "")).startswith("rejected_"))
    variables = sorted(set(
        r.get("target_variable", "") for r in records
        if r.get("target_variable") and not str(r.get("candidate_status", "")).startswith("rejected_")
    ))
    by_variable: dict[str, int] = {}
    for r in records:
        v = r.get("target_variable", "")
        if v and not str(r.get("candidate_status", "")).startswith("rejected_"):
            by_variable[v] = by_variable.get(v, 0) + 1
    return {
        "total": total,
        "candidate_found": found,
        "needs_review": nr,
        "rejected": rejected,
        "variables_covered": variables,
        "variables_covered_count": len(variables),
        "by_variable": by_variable,
        "missing_value_count": sum(
            1 for r in records if not r.get("raw_value", "").strip()
            and r.get("candidate_status") == "candidate_found"
        ),
        "missing_quote_count": sum(
            1 for r in records if not r.get("quote", "").strip()
        ),
    }


def _compute_variable_coverage(
    v1_workspaces: list[dict[str, Any]],
    v2_outputs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    v2_all_records: list[dict[str, Any]] = []
    for out in v2_outputs:
        v2_all_records.extend(read_csv(out["candidates_path"]))

    rows: list[dict[str, Any]] = []
    for var in _ALL_VARIABLES:
        v2_var_records = [
            r for r in v2_all_records
            if r.get("target_variable") == var
            and not str(r.get("candidate_status", "")).startswith("rejected_")
        ]
        rows.append({
            "variable": var,
            "v2_candidate_count": len(v2_var_records),
            "v2_with_value": sum(1 for r in v2_var_records if r.get("raw_value", "").strip()),
            "v2_with_unit": sum(1 for r in v2_var_records if r.get("raw_unit", "").strip()),
            "v2_with_quote": sum(1 for r in v2_var_records if r.get("quote", "").strip()),
        })
    return rows


def run_benchmark(
    v1_pilot_root: str | Path,
    v2_output_root: str | Path,
    manual_baseline_path: str | Path | None,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Compare V1 and V2 outputs. Returns benchmark summary."""
    v1_root = Path(v1_pilot_root)
    v2_root = Path(v2_output_root)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    v1_workspaces = _find_v1_workspaces(v1_root)
    v2_outputs = _find_v2_outputs(v2_root)

    # Aggregate V1 stats
    v1_totals: dict[str, int] = {"total": 0, "possible_indicator": 0, "needs_review": 0,
                                  "reject_candidate": 0, "missing_value": 0, "missing_quote": 0}
    v1_doc_rows: list[dict[str, Any]] = []
    for ws in v1_workspaces:
        stats = _load_v1_stats(ws["workspace_path"])
        v1_totals["total"] += stats["total"]
        v1_totals["possible_indicator"] += stats["possible_indicator"]
        v1_totals["needs_review"] += stats["needs_review"]
        v1_totals["reject_candidate"] += stats["reject_candidate"]
        v1_totals["missing_value"] += stats.get("missing_value_count", 0)
        v1_totals["missing_quote"] += stats.get("missing_quote_count", 0)
        v1_doc_rows.append({
            "company": ws["company"], "year": ws["year"], "doc_type": ws["doc_type"],
            "version": "v1",
            **{k: v for k, v in stats.items() if isinstance(v, (int, float))},
        })

    # Aggregate V2 stats
    v2_totals: dict[str, int] = {"total": 0, "candidate_found": 0, "needs_review": 0,
                                  "rejected": 0, "missing_value": 0, "missing_quote": 0}
    v2_doc_rows: list[dict[str, Any]] = []
    for out in v2_outputs:
        stats = _load_v2_stats(out["candidates_path"])
        v2_totals["total"] += stats["total"]
        v2_totals["candidate_found"] += stats["candidate_found"]
        v2_totals["needs_review"] += stats["needs_review"]
        v2_totals["rejected"] += stats["rejected"]
        v2_totals["missing_value"] += stats.get("missing_value_count", 0)
        v2_totals["missing_quote"] += stats.get("missing_quote_count", 0)
        v2_doc_rows.append({
            "output_dir": out["output_dir"],
            "version": "v2",
            **{k: v for k, v in stats.items() if not isinstance(v, (list, dict))},
        })

    # Variable coverage
    var_coverage = _compute_variable_coverage(v1_workspaces, v2_outputs)
    write_csv(out_dir / "v1_vs_v2_variable_coverage.csv", var_coverage,
              ["variable", "v2_candidate_count", "v2_with_value", "v2_with_unit", "v2_with_quote"])

    # Candidate counts comparison
    count_rows = [
        {"metric": "Total candidates", "v1": v1_totals["total"], "v2": v2_totals["total"]},
        {"metric": "Actionable (possible/found)", "v1": v1_totals["possible_indicator"], "v2": v2_totals["candidate_found"]},
        {"metric": "Needs review", "v1": v1_totals["needs_review"], "v2": v2_totals["needs_review"]},
        {"metric": "Rejected/noise", "v1": v1_totals["reject_candidate"], "v2": v2_totals["rejected"]},
        {"metric": "Missing values", "v1": v1_totals["missing_value"], "v2": v2_totals["missing_value"]},
        {"metric": "Missing quotes", "v1": v1_totals["missing_quote"], "v2": v2_totals["missing_quote"]},
        {"metric": "V1 docs processed", "v1": len(v1_workspaces), "v2": ""},
        {"metric": "V2 outputs found", "v1": "", "v2": len(v2_outputs)},
    ]
    write_csv(out_dir / "v1_vs_v2_candidate_counts.csv", count_rows, ["metric", "v1", "v2"])

    # Baseline comparison if available
    baseline_result: dict[str, Any] = {}
    if manual_baseline_path and Path(manual_baseline_path).exists():
        baseline_result = _compare_with_baseline(manual_baseline_path, v2_outputs)

    # Write markdown report
    _write_benchmark_report(out_dir, v1_totals, v2_totals, var_coverage,
                             v1_workspaces, v2_outputs, baseline_result)

    summary: dict[str, Any] = {
        "v1_documents": len(v1_workspaces),
        "v2_outputs": len(v2_outputs),
        "v1_totals": v1_totals,
        "v2_totals": v2_totals,
        "variables_covered_v2": sum(1 for r in var_coverage if r["v2_candidate_count"] > 0),
        "baseline_comparison": baseline_result,
        "output_dir": str(out_dir),
    }
    write_json(out_dir / "benchmark_summary.json", summary)
    return summary


def _compare_with_baseline(
    baseline_path: str | Path,
    v2_outputs: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline = read_csv(baseline_path)
    if not baseline:
        return {}

    manual_count = len(baseline)
    tp_column = [r for r in baseline if r.get("error_type", r.get("v1_error_type", "")) == "true_positive"]
    v1_found = len(tp_column)

    v2_all: list[dict[str, Any]] = []
    for out in v2_outputs:
        v2_all.extend(read_csv(out["candidates_path"]))

    # Simple coverage check: does V2 have a candidate for baseline indicator?
    v2_found = 0
    v2_fp_examples: list[str] = []
    for base_row in baseline:
        label = base_row.get("indicator", base_row.get("label", "")).lower()
        family = base_row.get("family", base_row.get("indicator_family", "")).lower()
        matched = [
            c for c in v2_all
            if (label in c.get("quote", "").lower() or label in c.get("target_variable", "").lower())
            and not str(c.get("candidate_status", "")).startswith("rejected_")
        ]
        if matched:
            v2_found += 1

    return {
        "manual_indicators_count": manual_count,
        "v1_found_count": v1_found,
        "v2_found_count": v2_found,
        "v1_false_positive_examples": len([r for r in baseline if "false_positive" in r.get("error_type", "")]),
        "v2_false_positive_examples": len(v2_fp_examples),
        "v1_missed_count": manual_count - v1_found,
        "v2_missed_count": manual_count - v2_found,
    }


def _write_benchmark_report(
    out_dir: Path,
    v1_totals: dict,
    v2_totals: dict,
    var_coverage: list[dict],
    v1_workspaces: list[dict],
    v2_outputs: list[dict],
    baseline_result: dict,
) -> None:
    lines = [
        "# V1 vs V2 Benchmark Report",
        "",
        f"**V1 documents processed**: {len(v1_workspaces)}",
        f"**V2 outputs found**: {len(v2_outputs)}",
        "",
        "## Candidate Counts",
        "",
        "| Metric | V1 | V2 |",
        "|--------|----|----|",
        f"| Total candidates | {v1_totals['total']} | {v2_totals['total']} |",
        f"| Actionable (possible/found) | {v1_totals['possible_indicator']} | {v2_totals['candidate_found']} |",
        f"| Needs review | {v1_totals['needs_review']} | {v2_totals['needs_review']} |",
        f"| Rejected/noise | {v1_totals['reject_candidate']} | {v2_totals['rejected']} |",
        f"| Missing values | {v1_totals['missing_value']} | {v2_totals['missing_value']} |",
        f"| Missing quotes | {v1_totals['missing_quote']} | {v2_totals['missing_quote']} |",
        "",
        "## Variable Coverage (V2)",
        "",
        "| Variable | V2 Candidates | With Value | With Unit | With Quote |",
        "|----------|--------------|------------|-----------|------------|",
    ]
    for r in var_coverage:
        lines.append(
            f"| {r['variable']} | {r['v2_candidate_count']} | "
            f"{r['v2_with_value']} | {r['v2_with_unit']} | {r['v2_with_quote']} |"
        )

    if baseline_result:
        lines.extend([
            "",
            "## Baseline Comparison (Schneider TCFD)",
            "",
            f"- Manual indicators identified: {baseline_result.get('manual_indicators_count', '?')}",
            f"- V1 found: {baseline_result.get('v1_found_count', '?')}",
            f"- V2 found: {baseline_result.get('v2_found_count', '?')}",
            f"- V1 missed: {baseline_result.get('v1_missed_count', '?')}",
            f"- V2 missed: {baseline_result.get('v2_missed_count', '?')}",
        ])

    lines.extend([
        "",
        "## Decision",
        "",
        "> V2 benchmark requires validation on full pilot (10 documents).",
        "> Do not declare V2 superior without complete metrics.",
        "> GO if: V2 is non-destructive, contract-valid, variable coverage ≥ V1.",
        "> GO_WITH_FIXES if: V2 works but coverage limited or false positives remain.",
        "> NO_GO if: V2 produces values without quotes, modifies sources, or crashes.",
    ])

    (out_dir / "v1_vs_v2_comparison_report.md").write_text("\n".join(lines), encoding="utf-8")
