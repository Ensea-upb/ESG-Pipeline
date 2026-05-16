"""Tests for benchmark module — report creation, V1 vs V2 comparison."""
import json
import pytest
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from ESGVariableTargetedExtractionV2.tests.helpers import make_sample_candidate, DOCUMENT_ID, COMPANY, FISCAL_YEAR
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.benchmark import run_benchmark
from ESGVariableTargetedExtractionV2.src.esg_variable_targeted_extraction_v2.io_utils import write_csv


def _make_fake_v2_output(base_dir: Path) -> Path:
    """Create a fake V2 output directory with targeted_candidates_v2.csv."""
    out_dir = base_dir / "test-company" / "2024" / "01_urd_annual_report" / "v2_smoke"
    out_dir.mkdir(parents=True, exist_ok=True)
    candidates = [
        make_sample_candidate("water_consumption", "4.2", "Mm3"),
        make_sample_candidate("co2_emissions", "457", "ktCO2e"),
        make_sample_candidate("human_capital", "52000", "employees"),
    ]
    write_csv(out_dir / "targeted_candidates_v2.csv", candidates)
    return out_dir


def _make_fake_v1_workspace(base_dir: Path) -> Path:
    """Create a fake V1 review workspace."""
    ws_dir = (base_dir / "test-company" / "2024" / "01_urd_annual_report" /
              f"canonical_{DOCUMENT_ID}_v1" / "04_review_workspace")
    ws_dir.mkdir(parents=True, exist_ok=True)
    v1_records = [
        {"validation_status": "possible_indicator", "indicator_family": "environmental",
         "raw_value": "4.2", "raw_unit": "Mm3", "quote": "water 4.2 Mm3"},
        {"validation_status": "needs_review", "indicator_family": "unknown",
         "raw_value": "", "raw_unit": "", "quote": "ISO 50001"},
        {"validation_status": "reject_candidate", "indicator_family": "unknown",
         "raw_value": "2.1", "raw_unit": "", "quote": "section 2.1"},
    ]
    write_csv(ws_dir / "manual_review_workspace.csv", v1_records)
    return ws_dir


def test_benchmark_report_created(tmp_path):
    v1_root = tmp_path / "v1_pilot"
    v2_root = tmp_path / "v2_outputs"
    out_dir = tmp_path / "benchmark_results"

    _make_fake_v1_workspace(v1_root)
    _make_fake_v2_output(v2_root)

    result = run_benchmark(v1_root, v2_root, None, out_dir)

    assert out_dir.exists(), "Benchmark output directory must be created"
    assert (out_dir / "v1_vs_v2_comparison_report.md").exists()
    assert (out_dir / "v1_vs_v2_candidate_counts.csv").exists()
    assert (out_dir / "v1_vs_v2_variable_coverage.csv").exists()
    assert (out_dir / "benchmark_summary.json").exists()


def test_benchmark_summary_has_expected_keys(tmp_path):
    v1_root = tmp_path / "v1_pilot"
    v2_root = tmp_path / "v2_outputs"
    out_dir = tmp_path / "benchmark_out"

    _make_fake_v1_workspace(v1_root)
    _make_fake_v2_output(v2_root)

    result = run_benchmark(v1_root, v2_root, None, out_dir)

    assert "v1_documents" in result
    assert "v2_outputs" in result
    assert "v1_totals" in result
    assert "v2_totals" in result


def test_benchmark_v1_counts_correct(tmp_path):
    v1_root = tmp_path / "v1_cnt"
    v2_root = tmp_path / "v2_cnt"
    out_dir = tmp_path / "bench_cnt"

    _make_fake_v1_workspace(v1_root)
    _make_fake_v2_output(v2_root)

    result = run_benchmark(v1_root, v2_root, None, out_dir)

    assert result["v1_totals"]["total"] == 3
    assert result["v1_totals"]["possible_indicator"] == 1
    assert result["v1_totals"]["needs_review"] == 1
    assert result["v1_totals"]["reject_candidate"] == 1


def test_benchmark_with_baseline(tmp_path):
    v1_root = tmp_path / "v1_base"
    v2_root = tmp_path / "v2_base"
    out_dir = tmp_path / "bench_base"
    baseline_path = tmp_path / "baseline.csv"

    _make_fake_v1_workspace(v1_root)
    _make_fake_v2_output(v2_root)

    # Write simple baseline
    baseline_records = [
        {"indicator": "water withdrawal", "family": "water_consumption",
         "value": "4.2", "unit": "Mm3", "error_type": "true_positive"},
        {"indicator": "CO2 scope 1", "family": "co2_emissions",
         "value": "457", "unit": "ktCO2e", "error_type": "true_positive"},
    ]
    write_csv(baseline_path, baseline_records)

    result = run_benchmark(v1_root, v2_root, baseline_path, out_dir)
    assert "baseline_comparison" in result
    assert result["baseline_comparison"].get("manual_indicators_count", 0) >= 0


def test_benchmark_empty_inputs_no_crash(tmp_path):
    v1_root = tmp_path / "empty_v1"
    v2_root = tmp_path / "empty_v2"
    out_dir = tmp_path / "empty_out"
    v1_root.mkdir()
    v2_root.mkdir()

    result = run_benchmark(v1_root, v2_root, None, out_dir)
    assert isinstance(result, dict)
    assert result["v1_documents"] == 0
    assert result["v2_outputs"] == 0
