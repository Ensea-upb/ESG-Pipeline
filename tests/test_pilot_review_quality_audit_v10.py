"""
test_pilot_review_quality_audit_v10.py
=======================================
Tests for PilotReviewQualityAudit v1.0 (tools/audit_pilot_review_quality.py).

All tests use synthetic fixtures — independent of the real pilot output.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

# Ensure tools/ is importable
_ROOT = Path(__file__).resolve().parents[1]
_TOOLS = _ROOT / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import audit_pilot_review_quality as aq


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_row(
    doc_id: str = "canonical_abc",
    company: str = "test-co",
    fiscal_year: str = "2024",
    status: str = "possible_indicator",
    family: str = "ghg_emissions",
    raw_value: str = "100",
    raw_unit: str = "tCO2e",
    normalized_year: str = "2024",
    page_number: str = "42",
    quote: str = "The company reduced GHG emissions by 100 tCO2e in 2024.",
    label: str = "ghg scope 1 emissions",
    review_item_id: str = "review_item_000001",
    candidate_id: str = "csv:canonical_abc:observed_metric",
    source_engine: str = "csv",
    indicator_key_candidate: str = "ghg_emissions:scope_1",
    normalized_value: str = "100",
    normalized_unit: str = "tCO2e",
) -> dict:
    return {
        "review_item_id": review_item_id,
        "candidate_id": candidate_id,
        "document_id": doc_id,
        "company": company,
        "fiscal_year": fiscal_year,
        "source_engine": source_engine,
        "validation_status": status,
        "indicator_family": family,
        "indicator_key_candidate": indicator_key_candidate,
        "label": label,
        "raw_value": raw_value,
        "raw_unit": raw_unit,
        "normalized_value": normalized_value,
        "normalized_unit": normalized_unit,
        "normalized_year": normalized_year,
        "page_number": page_number,
        "section_id": "",
        "evidence_id": "",
        "table_id": "",
        "cell_id": "",
        "figure_id": "",
        "quote": quote,
        "confidence": "0.8",
        "review_priority": "high",
        "review_reason": "numeric value detected",
        "suggested_review_action": "confirm",
        "human_decision": "",
        "human_decision_reason": "",
        "reviewer_notes": "",
    }


_CSV_FIELDNAMES = list(_make_row().keys())


def _write_workspace(ws_dir: Path, rows: list[dict]) -> None:
    ws_dir.mkdir(parents=True, exist_ok=True)
    csv_path = ws_dir / "manual_review_workspace.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def _make_pilot(tmp_path: Path, doc_specs: list[dict]) -> Path:
    """
    Build a synthetic pilot-root with multiple 04_review_workspace directories.

    doc_specs is a list of dicts with keys:
      company_slug, fiscal_year, official_doc_type, document_id, rows
    """
    pilot_root = tmp_path / "pilot"
    pilot_root.mkdir()

    per_document = []
    for spec in doc_specs:
        ws_dir = (
            pilot_root
            / spec["company_slug"]
            / spec["fiscal_year"]
            / spec["official_doc_type"]
            / spec["document_id"]
            / "04_review_workspace"
        )
        _write_workspace(ws_dir, spec["rows"])
        per_document.append(
            {
                "document_id": spec["document_id"],
                "company_slug": spec["company_slug"],
                "company_name": spec.get("company_name", spec["company_slug"].title()),
                "fiscal_year": spec["fiscal_year"],
                "official_doc_type": spec["official_doc_type"],
                "final_path": "",
                "status": "success",
                "steps_completed": ["step_01", "step_02", "step_03", "step_04"],
                "error": None,
                "review_workspace_produced": True,
            }
        )

    summary = {
        "documents_selected": len(doc_specs),
        "documents_processed": len(doc_specs),
        "documents_success": len(doc_specs),
        "documents_failed": 0,
        "per_document": per_document,
    }
    (pilot_root / "pilot_run_summary.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )
    return pilot_root


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_audit_script_exists():
    """tools/audit_pilot_review_quality.py must exist."""
    script = _ROOT / "tools" / "audit_pilot_review_quality.py"
    assert script.is_file(), f"Audit script missing: {script}"


def test_finds_review_workspaces(tmp_path: Path):
    """find_workspace_dirs must locate all 04_review_workspace directories."""
    pilot_root = _make_pilot(
        tmp_path,
        [
            {
                "company_slug": "acme",
                "fiscal_year": "2024",
                "official_doc_type": "01_annual_report",
                "document_id": "canonical_aaa",
                "rows": [_make_row(doc_id="canonical_aaa", company="acme")],
            },
            {
                "company_slug": "globex",
                "fiscal_year": "2024",
                "official_doc_type": "02_sustainability",
                "document_id": "canonical_bbb",
                "rows": [_make_row(doc_id="canonical_bbb", company="globex")],
            },
        ],
    )
    ws_dirs = aq.find_workspace_dirs(pilot_root)
    assert len(ws_dirs) == 2, f"Expected 2 workspace dirs, found {len(ws_dirs)}"
    names = [d.parent.name for d in ws_dirs]
    assert "canonical_aaa" in names
    assert "canonical_bbb" in names


def test_counts_candidates_by_document(tmp_path: Path):
    """compute_doc_stats must return accurate counts per validation_status."""
    rows = [
        _make_row(status="possible_indicator"),
        _make_row(status="possible_indicator"),
        _make_row(status="needs_review"),
        _make_row(status="reject_candidate"),
    ]
    path_meta = {
        "company_slug": "acme",
        "fiscal_year": "2024",
        "official_doc_type": "01_annual_report",
        "document_id": "canonical_aaa",
    }
    stats = aq.compute_doc_stats(rows, path_meta, "Acme Corp")

    assert stats["review_items_count"] == 4
    assert stats["possible_indicator_count"] == 2
    assert stats["needs_review_count"] == 1
    assert stats["reject_candidate_count"] == 1


def test_counts_candidates_by_family(tmp_path: Path):
    """compute_family_stats must aggregate correctly by indicator_family."""
    rows = [
        _make_row(family="ghg_emissions", status="possible_indicator"),
        _make_row(family="ghg_emissions", status="needs_review"),
        _make_row(family="energy", status="possible_indicator"),
        _make_row(family="energy", status="reject_candidate"),
        _make_row(family="energy", status="reject_candidate"),
    ]
    stats = aq.compute_family_stats(rows)

    fam_map = {d["indicator_family"]: d for d in stats}
    assert "ghg_emissions" in fam_map
    assert "energy" in fam_map

    ghg = fam_map["ghg_emissions"]
    assert ghg["total_candidates"] == 2
    assert ghg["possible_indicator_count"] == 1
    assert ghg["needs_review_count"] == 1

    energy = fam_map["energy"]
    assert energy["total_candidates"] == 3
    assert energy["possible_indicator_count"] == 1
    assert energy["reject_candidate_count"] == 2

    # shares must sum to 100
    total_share = sum(d["share_of_total_candidates"] for d in stats)
    assert abs(total_share - 100.0) < 0.1


def test_detects_missing_quotes(tmp_path: Path):
    """compute_doc_stats must count rows with empty quote correctly."""
    rows = [
        _make_row(quote=""),
        _make_row(quote="   "),
        _make_row(quote="Valid quote with enough characters to not be short."),
    ]
    path_meta = {
        "company_slug": "acme",
        "fiscal_year": "2024",
        "official_doc_type": "01_annual_report",
        "document_id": "canonical_aaa",
    }
    stats = aq.compute_doc_stats(rows, path_meta, "Acme")
    assert stats["quote_missing_count"] == 2


def test_detects_false_positive_footnote(tmp_path: Path):
    """
    A row with raw_value in [1-6] AND label containing 'refer to glossary'
    must be classified as high-risk false positive with reason 'likely_footnote_value'.
    """
    row = _make_row(
        raw_value="3",
        label="refer to glossary for methodology",
        quote="",
    )
    path_meta = {
        "company_slug": "acme",
        "fiscal_year": "2024",
        "official_doc_type": "01_annual_report",
        "document_id": "canonical_aaa",
    }
    fp_rows = aq.detect_false_positives([row], path_meta)
    assert len(fp_rows) >= 1, "Must detect false positive for footnote-value pattern"
    reasons = fp_rows[0]["risk_reason"]
    assert "likely_footnote_value" in reasons or "footnote_label" in reasons
    assert fp_rows[0]["risk_level"] == "high"


def test_detects_year_mismatch(tmp_path: Path):
    """
    A candidate with fiscal_year=2024 and normalized_year=2015 must be flagged
    with risk_reason containing 'year_mismatch'.
    """
    row = _make_row(
        fiscal_year="2024",
        normalized_year="2015",
        quote="Some valid long quote about energy consumption in 2015.",
    )
    path_meta = {
        "company_slug": "acme",
        "fiscal_year": "2024",
        "official_doc_type": "01_annual_report",
        "document_id": "canonical_aaa",
    }
    fp_rows = aq.detect_false_positives([row], path_meta)
    reasons_all = [r["risk_reason"] for r in fp_rows]
    assert any("year_mismatch" in r for r in reasons_all), (
        f"Expected year_mismatch in false positive reasons, got: {reasons_all}"
    )


def test_top_possible_indicators_limit(tmp_path: Path):
    """get_top_candidates must return at most 30 rows per document."""
    # Create 50 rows for a single document
    rows = [
        _make_row(
            doc_id="canonical_aaa",
            review_item_id=f"review_item_{i:06d}",
            candidate_id=f"csv:canonical_aaa:obs_{i}",
            status="possible_indicator",
        )
        for i in range(50)
    ]
    path_meta_by_doc = {"canonical_aaa": {"company_slug": "acme", "official_doc_type": "01_ar"}}
    name_by_slug = {"acme": "Acme Corp"}

    result = aq.get_top_candidates(rows, path_meta_by_doc, name_by_slug, max_per_doc=30, global_max=200)
    assert len(result) <= 30, f"Expected ≤30 candidates, got {len(result)}"


def test_outputs_are_created(tmp_path: Path):
    """run_audit must create all 8 expected output files."""
    pilot_root = _make_pilot(
        tmp_path,
        [
            {
                "company_slug": "acme",
                "company_name": "Acme Corp",
                "fiscal_year": "2024",
                "official_doc_type": "01_annual_report",
                "document_id": "canonical_aaa",
                "rows": [
                    _make_row(doc_id="canonical_aaa", company="acme", status="possible_indicator"),
                    _make_row(doc_id="canonical_aaa", company="acme", status="needs_review"),
                    _make_row(doc_id="canonical_aaa", company="acme", status="reject_candidate"),
                ],
            }
        ],
    )
    output_dir = tmp_path / "audit_out"
    rc = aq.run_audit(pilot_root, output_dir, overwrite=True)
    assert rc == 0

    expected_files = [
        "pilot_review_quality_summary.json",
        "candidate_counts_by_document.csv",
        "candidate_counts_by_family.csv",
        "candidate_counts_by_status.csv",
        "top_possible_indicators_all_docs.csv",
        "false_positive_risk_samples.csv",
        "review_burden_report.md",
        "PILOT_REVIEW_QUALITY_AUDIT_REPORT.md",
    ]
    for fname in expected_files:
        fpath = output_dir / fname
        assert fpath.exists(), f"Expected output file missing: {fname}"


def test_audit_is_read_only(tmp_path: Path):
    """run_audit must not modify any file inside the pilot_root."""
    pilot_root = _make_pilot(
        tmp_path,
        [
            {
                "company_slug": "acme",
                "company_name": "Acme Corp",
                "fiscal_year": "2024",
                "official_doc_type": "01_annual_report",
                "document_id": "canonical_aaa",
                "rows": [_make_row(doc_id="canonical_aaa", company="acme")],
            }
        ],
    )

    # Capture all files under pilot_root with their modification times
    def _snapshot(root: Path) -> dict[str, float]:
        return {
            str(p.relative_to(root)): p.stat().st_mtime
            for p in root.rglob("*")
            if p.is_file()
        }

    before = _snapshot(pilot_root)

    output_dir = tmp_path / "audit_out"
    aq.run_audit(pilot_root, output_dir, overwrite=True)

    after = _snapshot(pilot_root)

    assert before == after, (
        "run_audit modified files inside pilot_root (read-only constraint violated).\n"
        f"Changed: {set(after.items()) - set(before.items())}"
    )


def test_summary_has_decision_field(tmp_path: Path):
    """pilot_review_quality_summary.json must contain decision_recommendation."""
    pilot_root = _make_pilot(
        tmp_path,
        [
            {
                "company_slug": "acme",
                "company_name": "Acme Corp",
                "fiscal_year": "2024",
                "official_doc_type": "01_annual_report",
                "document_id": "canonical_aaa",
                "rows": [_make_row(doc_id="canonical_aaa", company="acme")],
            }
        ],
    )
    output_dir = tmp_path / "audit_out"
    aq.run_audit(pilot_root, output_dir, overwrite=True)

    summary = json.loads((output_dir / "pilot_review_quality_summary.json").read_text(encoding="utf-8"))
    assert "decision_recommendation" in summary
    assert summary["decision_recommendation"] in {"GO", "GO_WITH_FIXES", "NO_GO"}
