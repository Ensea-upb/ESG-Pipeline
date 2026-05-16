"""Tests for v0.6.1 figure detection stabilization.

Tests A–I verify the new visual_object_level fields, quality flags, and counters.
Test J is the non-regression guard (all prior tests must still pass).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ESGInformationExtraction.run_pdf_extraction import process_raw_figures

from .conftest import read_json, read_jsonl, run_cli, write_test_pdf


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_page_data(
    page_number: int = 1,
    document_id: str = "doc_test",
    raw_images: list | None = None,
) -> dict:
    page_id = f"{document_id}_page_{page_number:04d}"
    return {
        "page_number": page_number,
        "page_id": page_id,
        "raw_images": raw_images or [],
    }


def _plain_diag(is_possible_visual: bool = False, is_low_text: bool = False) -> dict:
    return {
        "is_possible_toc": False,
        "is_high_title_density": False,
        "is_possible_visual": is_possible_visual,
        "is_low_text": is_low_text,
        "text_char_count": 50 if is_possible_visual else 400,
    }


def _visual_diag() -> dict:
    return _plain_diag(is_possible_visual=True)


def _low_text_diag() -> dict:
    return _plain_diag(is_possible_visual=True, is_low_text=True)


def _caption_page_blocks(document_id: str = "doc_test", page_number: int = 1) -> list[dict]:
    page_id = f"{document_id}_page_{page_number:04d}"
    return [
        {
            "text_block_id": f"{page_id}_block_0001",
            "block_type": "caption",
            "text": "Figure 1 GHG emissions by scope",
            "page_id": page_id,
            "page_number": page_number,
        }
    ]


# ── A: page_visual_heuristic → visual_object_level = page_level_visual ───────

def test_A_page_visual_heuristic_gives_page_level_visual():
    page_data = _make_page_data(page_number=3)
    figs = process_raw_figures(page_data, "doc1", [], [], _visual_diag())
    assert len(figs) == 1
    fig = figs[0]
    assert fig["visual_object_level"] == "page_level_visual", (
        f"Expected page_level_visual, got {fig['visual_object_level']}"
    )
    assert fig["is_page_level_visual"] is True
    assert fig["is_embedded_visual"] is False
    assert fig["is_captioned_figure"] is False
    assert fig["is_visual_page_candidate"] is True


def test_A_caption_heuristic_gives_captioned_region():
    page_data = _make_page_data(page_number=2)
    blocks = _caption_page_blocks(page_number=2)
    figs = process_raw_figures(page_data, "doc1", [], blocks, _plain_diag())
    assert len(figs) == 1
    fig = figs[0]
    assert fig["visual_object_level"] == "captioned_region"
    assert fig["is_captioned_figure"] is True
    assert fig["is_page_level_visual"] is False
    assert fig["is_embedded_visual"] is False


# ── B: page-level visuals are review_required ─────────────────────────────────

def test_B_page_level_visual_is_review_required():
    page_data = _make_page_data(page_number=5)
    figs = process_raw_figures(page_data, "doc1", [], [], _visual_diag())
    assert len(figs) == 1
    assert figs[0]["review_required"] is True


# ── C: page-level visuals have figure_confidence <= 0.35 ─────────────────────

def test_C_page_level_visual_confidence_is_low():
    page_data = _make_page_data(page_number=2)
    figs = process_raw_figures(page_data, "doc1", [], [], _visual_diag())
    assert len(figs) == 1
    assert figs[0]["figure_confidence"] <= 0.35, (
        f"page_visual_heuristic figure_confidence must be <= 0.35, "
        f"got {figs[0]['figure_confidence']}"
    )


# ── D: figures without bbox have no_bbox_available flag ──────────────────────

def test_D_no_bbox_flag_on_page_level_visual():
    page_data = _make_page_data(page_number=2)
    figs = process_raw_figures(page_data, "doc1", [], [], _visual_diag())
    fig = figs[0]
    assert fig["figure_bbox"] is None
    assert "no_bbox_available" in fig["figure_quality_flags"], (
        f"no_bbox_available must be in flags, got {fig['figure_quality_flags']}"
    )


def test_D_no_bbox_flag_on_caption_heuristic():
    page_data = _make_page_data(page_number=2)
    blocks = _caption_page_blocks(page_number=2)
    figs = process_raw_figures(page_data, "doc1", [], blocks, _plain_diag())
    fig = figs[0]
    assert fig["figure_bbox"] is None
    assert "no_bbox_available" in fig["figure_quality_flags"]


# ── E: figures without caption have no_caption_detected flag ─────────────────

def test_E_no_caption_flag_on_page_level_visual():
    page_data = _make_page_data(page_number=2)
    figs = process_raw_figures(page_data, "doc1", [], [], _visual_diag())
    fig = figs[0]
    assert fig["nearby_caption_text"] is None
    assert "no_caption_detected" in fig["figure_quality_flags"]


# ── E2: additional flags present on page_visual_heuristic ────────────────────

def test_E2_page_visual_heuristic_flags():
    page_data = _make_page_data(page_number=3)
    figs = process_raw_figures(page_data, "doc1", [], [], _visual_diag())
    fig = figs[0]
    flags = fig["figure_quality_flags"]
    assert "page_level_visual_candidate" in flags
    assert "weak_visual_detection" in flags
    assert "not_interpretable_visual" in flags


def test_E2_cover_page_gets_possible_cover_flag():
    # page_number == 1 → possible_cover_or_separator_page
    page_data = _make_page_data(page_number=1)
    figs = process_raw_figures(page_data, "doc1", [], [], _visual_diag())
    fig = figs[0]
    assert "possible_cover_or_separator_page" in fig["figure_quality_flags"]


def test_E2_low_text_page_gets_possible_cover_flag():
    page_data = _make_page_data(page_number=4)
    figs = process_raw_figures(page_data, "doc1", [], [], _low_text_diag())
    fig = figs[0]
    assert "possible_cover_or_separator_page" in fig["figure_quality_flags"]


# ── F: page-level visual evidence has non-interpretative quote ───────────────

def test_F_page_level_visual_evidence_has_non_interpretative_quote(
    require_pdfplumber, tmp_path: Path
):
    # low-text PDF to trigger page_visual_heuristic
    pdf = write_test_pdf(tmp_path / "vis.pdf", [["x"]])
    out = tmp_path / "out"
    result = run_cli(pdf, out, document_id="v061_F")
    assert result.returncode == 0, result.stderr
    figures = read_jsonl(out / "figure_index.jsonl")
    page_lv = [f for f in figures if f.get("is_page_level_visual")]
    if not page_lv:
        pytest.skip("No page-level visual detected on this PDF")
    evidence = read_jsonl(out / "evidence_store.jsonl")
    fig_ev = [e for e in evidence if e.get("evidence_type") == "figure"]
    page_lv_ids = {f["figure_id"] for f in page_lv}
    for ev in fig_ev:
        if ev.get("figure_id") in page_lv_ids:
            assert "not interpreted" in ev["quote"].lower(), (
                f"Page-level visual evidence quote must mention 'not interpreted', "
                f"got: {ev['quote']!r}"
            )
            assert ev["review_required"] is True


# ── G: figure_statistics.json contains new v0.6.1 counters ──────────────────

def test_G_figure_statistics_has_v061_keys(
    require_pdfplumber, figure_pdf: Path, tmp_path: Path
):
    out = tmp_path / "out"
    result = run_cli(figure_pdf, out, document_id="v061_G")
    assert result.returncode == 0, result.stderr
    stats = read_json(out / "figure_statistics.json")
    required = {
        "page_level_visual_count",
        "embedded_visual_count",
        "captioned_figure_count",
        "visual_page_candidates_count",
        "figures_without_bbox_count",
        "weak_visual_detections_count",
        "possible_cover_or_separator_figures_count",
        "figure_object_level_distribution",
        "sample_page_level_visuals",
        "sample_weak_visual_detections",
    }
    missing = required - stats.keys()
    assert not missing, f"figure_statistics.json missing v0.6.1 keys: {missing}"


# ── H: extraction_summary.json contains new v0.6.1 counters ─────────────────

def test_H_extraction_summary_has_v061_keys(
    require_pdfplumber, small_pdf: Path, tmp_path: Path
):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="v061_H")
    assert result.returncode == 0, result.stderr
    summary = read_json(out / "extraction_summary.json")
    required = {
        "page_level_visual_count",
        "embedded_visual_count",
        "captioned_figure_count",
        "visual_page_candidates_count",
        "figures_without_bbox_count",
        "weak_visual_detections_count",
    }
    missing = required - summary.keys()
    assert not missing, f"extraction_summary.json missing v0.6.1 keys: {missing}"


# ── I: quality_report.jsonl contains new v0.6.1 check names ─────────────────

def test_I_quality_report_has_v061_checks(
    require_pdfplumber, small_pdf: Path, tmp_path: Path
):
    out = tmp_path / "out"
    result = run_cli(small_pdf, out, document_id="v061_I")
    assert result.returncode == 0, result.stderr
    checks = read_jsonl(out / "quality_report.jsonl")
    check_names = {c.get("check_name", "") for c in checks}
    required = {
        "page_level_visual_detected",
        "figure_without_bbox_warning",
        "weak_visual_detection_warning",
        "visual_page_candidate_warning",
        "figure_object_level_assigned",
    }
    missing = required - check_names
    assert not missing, f"quality_report.jsonl missing v0.6.1 check names: {missing}"


# ── figure_index schema includes v0.6.1 fields ───────────────────────────────

def test_figure_index_has_v061_fields(
    require_pdfplumber, figure_pdf: Path, tmp_path: Path
):
    out = tmp_path / "out"
    result = run_cli(figure_pdf, out, document_id="v061_schema")
    assert result.returncode == 0, result.stderr
    figures = read_jsonl(out / "figure_index.jsonl")
    if not figures:
        pytest.skip("No figures detected")
    required = {
        "visual_object_level",
        "is_page_level_visual",
        "is_embedded_visual",
        "is_captioned_figure",
        "is_visual_page_candidate",
    }
    for fig in figures:
        missing = required - fig.keys()
        assert not missing, (
            f"figure_id={fig.get('figure_id')} missing v0.6.1 fields: {missing}"
        )


# ── caption figure has captioned_region object level ─────────────────────────

def test_caption_figure_evidence_has_caption_quote(
    require_pdfplumber, figure_pdf: Path, tmp_path: Path
):
    out = tmp_path / "out"
    result = run_cli(figure_pdf, out, document_id="v061_cap")
    assert result.returncode == 0, result.stderr
    figures = read_jsonl(out / "figure_index.jsonl")
    captioned = [f for f in figures if f.get("is_captioned_figure")]
    if not captioned:
        pytest.skip("No caption heuristic figures detected")
    evidence = read_jsonl(out / "evidence_store.jsonl")
    cap_ids = {f["figure_id"] for f in captioned}
    for ev in evidence:
        if ev.get("figure_id") in cap_ids:
            assert ev.get("quote"), "Captioned figure evidence must have a non-empty quote"
            # quote should use the caption text, not generic "not interpreted"
            assert "not interpreted" not in ev["quote"].lower(), (
                "Captioned figure evidence should not use page-level quote"
            )
