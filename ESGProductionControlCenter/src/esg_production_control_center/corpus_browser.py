"""
corpus_browser.py — Browse ESGFinalCorpus and link PDFs to pipeline run outputs.
Read-only. Never modifies source files.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CORPUS_ROOT = _PROJECT_ROOT / "ESGFinalCorpus"


def get_corpus_root(project_root: str | Path | None = None) -> Path:
    if project_root is None:
        return _CORPUS_ROOT
    return Path(project_root) / "ESGFinalCorpus"


def browse_corpus(corpus_root: str | Path) -> dict[str, dict[str, dict[str, Path]]]:
    """Return nested dict: company -> year -> doc_type -> pdf_path."""
    root = Path(corpus_root)
    result: dict[str, dict[str, dict[str, Path]]] = {}
    if not root.exists():
        return result
    for company_dir in sorted(root.iterdir()):
        if not company_dir.is_dir():
            continue
        company = company_dir.name
        result[company] = {}
        for year_dir in sorted(company_dir.iterdir()):
            if not year_dir.is_dir():
                continue
            year = year_dir.name
            result[company][year] = {}
            for doc_dir in sorted(year_dir.iterdir()):
                if not doc_dir.is_dir():
                    continue
                pdf = doc_dir / "document.pdf"
                if pdf.exists():
                    result[company][year][doc_dir.name] = pdf
    # Remove empty entries
    result = {c: {y: dt for y, dt in ys.items() if dt} for c, ys in result.items() if ys}
    return result


def get_all_pdfs(corpus_root: str | Path) -> list[dict[str, Any]]:
    """Return flat list of all corpus PDFs with metadata."""
    tree = browse_corpus(corpus_root)
    pdfs = []
    for company, years in tree.items():
        for year, doc_types in years.items():
            for doc_type, pdf_path in doc_types.items():
                pdfs.append({
                    "company": company,
                    "year": year,
                    "doc_type": doc_type,
                    "pdf_path": str(pdf_path),
                    "label": f"{company} / {year} / {doc_type}",
                })
    return pdfs


def find_doc_workspace(
    run_root: str | Path, company: str, year: str, doc_type: str
) -> Path | None:
    """Return the canonical document dir for company/year/doc_type in run_root, or None."""
    doc_dir = Path(run_root) / company / year / doc_type
    if not doc_dir.exists():
        return None
    for d in sorted(doc_dir.iterdir()):
        if d.is_dir() and d.name.startswith("canonical_"):
            return d
    return None


def render_pdf_page(pdf_path: str | Path, page_number: int = 0, dpi: int = 150) -> bytes | None:
    """Render one PDF page as PNG bytes. Returns None on failure."""
    try:
        import pymupdf
        doc = pymupdf.open(str(pdf_path))
        n = len(doc)
        if n == 0:
            return None
        page_number = max(0, min(page_number, n - 1))
        page = doc[page_number]
        zoom = dpi / 72.0
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return pix.tobytes("png")
    except Exception:
        return None


def get_pdf_page_count(pdf_path: str | Path) -> int:
    """Return number of pages in a PDF, or 0 on error."""
    try:
        import pymupdf
        doc = pymupdf.open(str(pdf_path))
        return len(doc)
    except Exception:
        return 0


def load_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_jsonl_head(path: Path, n: int = 100) -> list[dict[str, Any]]:
    """Load first n lines of a .jsonl file."""
    if not path.exists():
        return []
    rows = []
    try:
        with path.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= n:
                    break
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
    except Exception:
        pass
    return rows


def list_crops(doc_workspace: Path) -> list[Path]:
    """Return sorted list of visual crop PNG files."""
    crops_dir = doc_workspace / "02_orchestrator" / "visual" / "crops"
    if not crops_dir.exists():
        return []
    return sorted(crops_dir.glob("*.png"))


def get_stage_status(doc_workspace: Path) -> dict[str, bool]:
    """Return presence status for each pipeline stage in a doc workspace."""
    return {
        "01_information_extraction": (doc_workspace / "01_information_extraction").exists(),
        "02_orchestrator_csv": (doc_workspace / "02_orchestrator" / "csv").exists(),
        "02_orchestrator_visual": (doc_workspace / "02_orchestrator" / "visual").exists(),
        "02_orchestrator_table": (doc_workspace / "02_orchestrator" / "table").exists(),
        "04_review_workspace": (doc_workspace / "04_review_workspace").exists(),
    }
