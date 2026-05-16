from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "ESGInformationExtraction" / "run_pdf_extraction.py"


def pytest_configure(config):
    config.addinivalue_line("markers", "pdfplumber: requires pdfplumber")


@pytest.fixture
def require_pdfplumber():
    if importlib.util.find_spec("pdfplumber") is None:
        pytest.skip("pdfplumber is not installed")


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_test_pdf(pdf_path: Path, pages: list[list[str]], start_y: int = 720) -> Path:
    page_objects = []
    content_objects = []
    font_object_number = 3 + (2 * len(pages))

    for page_index, lines in enumerate(pages):
        content_object_number = 4 + (2 * page_index)
        text_ops = ["BT", "/F1 18 Tf", f"72 {start_y} Td", f"({_pdf_escape(lines[0])}) Tj"]
        for line in lines[1:]:
            text_ops.extend(["0 -28 Td", "/F1 12 Tf", f"({_pdf_escape(line)}) Tj"])
        text_ops.append("ET")
        stream = "\n".join(text_ops).encode("ascii")
        page_objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            + f"/Resources << /Font << /F1 {font_object_number} 0 R >> >> ".encode("ascii")
            + f"/Contents {content_object_number} 0 R >>".encode("ascii")
        )
        content_objects.append(
            b"<< /Length "
            + str(len(stream)).encode("ascii")
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )

    kids = " ".join(f"{3 + (2 * i)} 0 R" for i in range(len(pages))).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [" + kids + b"] /Count " + str(len(pages)).encode("ascii") + b" >>",
    ]
    for page_obj, content_obj in zip(page_objects, content_objects):
        objects.extend([page_obj, content_obj])
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    payload = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(payload))
        payload.extend(f"{index} 0 obj\n".encode("ascii"))
        payload.extend(obj)
        payload.extend(b"\nendobj\n")
    xref_offset = len(payload)
    payload.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    payload.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    pdf_path.write_bytes(bytes(payload))
    return pdf_path


@pytest.fixture
def small_pdf(tmp_path: Path) -> Path:
    return write_test_pdf(
        tmp_path / "sample.pdf",
        [
            [
                "SUSTAINABILITY REPORT",
                "This is a small PDF used for contract testing.",
                "Climate strategy and energy transition are discussed here.",
            ]
        ],
    )


@pytest.fixture
def low_text_pdf(tmp_path: Path) -> Path:
    return write_test_pdf(tmp_path / "low_text.pdf", [["LOW TEXT", "short"]])


@pytest.fixture
def toc_pdf(tmp_path: Path) -> Path:
    return write_test_pdf(
        tmp_path / "toc.pdf",
        [[
            "CLIMATE STRATEGY 12",
            "ENERGY TRANSITION 14",
            "GREENHOUSE GAS EMISSIONS 18",
            "WATER MANAGEMENT 22",
            "WASTE MANAGEMENT 26",
            "BIODIVERSITY 30",
            "WORKFORCE 34",
            "GOVERNANCE 40",
            "ASSURANCE 45",
        ]],
    )


@pytest.fixture
def list_pdf(tmp_path: Path) -> Path:
    return write_test_pdf(
        tmp_path / "list.pdf",
        [[
            "SUSTAINABILITY ACTIONS",
            "- Reduce emissions",
            "* Improve energy efficiency",
            "1. Publish transition plan",
            "(a) Review governance",
        ]],
    )


@pytest.fixture
def caption_pdf(tmp_path: Path) -> Path:
    return write_test_pdf(
        tmp_path / "caption.pdf",
        [[
            "CLIMATE DATA",
            "Table 1 Energy consumption by region",
            "Figure 1 Greenhouse gas emissions trend",
            "Graphique 2 Evolution des emissions",
        ]],
    )


@pytest.fixture
def footer_pdf(tmp_path: Path) -> Path:
    return write_test_pdf(
        tmp_path / "footer.pdf",
        [
            [
                "2024 Universal Registration Document 3",
                "4 2024 Universal Registration Document",
            ],
        ],
        start_y=72,
    )


@pytest.fixture
def footnote_pdf(tmp_path: Path) -> Path:
    return write_test_pdf(
        tmp_path / "footnote.pdf",
        [["(1) Renewal of term of office as a Director proposed at the annual Shareholders Meeting."]],
        start_y=72,
    )


@pytest.fixture
def historical_bottom_pdf(tmp_path: Path) -> Path:
    return write_test_pdf(
        tmp_path / "historical_bottom.pdf",
        [["1944 Le Parisien-Aujourd hui en France 2017 Fenty Beauty by Rihanna"]],
        start_y=72,
    )


@pytest.fixture
def section_pdf(tmp_path: Path) -> Path:
    return write_test_pdf(
        tmp_path / "sections.pdf",
        [[
            "ENVIRONMENT",
            "This paragraph belongs to environment.",
            "SOCIAL",
            "This paragraph belongs to social.",
            "GOVERNANCE",
            "This paragraph belongs to governance.",
        ]],
    )


@pytest.fixture
def timeline_title_pdf(tmp_path: Path) -> Path:
    return write_test_pdf(
        tmp_path / "timeline.pdf",
        [[
            "14th century 1365 Le Clos des Lambrays 1947 Parfums Christian Dior",
            "ENVIRONMENT",
            "Useful content.",
        ]],
    )


@pytest.fixture
def section_stabilization_pdf(tmp_path: Path) -> Path:
    return write_test_pdf(
        tmp_path / "section_stabilization.pdf",
        [[
            "CONTENTS",
            "UNIVERSAL REGISTRATION DOCUMENT",
            "FISCAL YEAR ENDED DECEMBER 31, 2024",
            "1952 Givenchy",
            "1916 Acqua di Parma Chateau d Esclans",
            "19,571 ( EUR millions)",
            "FINANCIAL HIGHLIGHTS",
            "RISK FACTORS AND MANAGEMENT",
        ]],
    )


@pytest.fixture
def section_false_positive_pdf(tmp_path: Path) -> Path:
    return write_test_pdf(
        tmp_path / "section_false_positive.pdf",
        [[
            "BUSINESS OVERVIEW,",
            "HIGHLIGHTS AND OUTLOOK",
            "(FROM FEBRUARY 1, 2025)",
            "OF THE GROUP AS OF DECEMBER 31, 2024",
            "LVMH",
            "OTHER HOLDING",
            "COMPANIES",
            "100% 50% Citadelles 100% 100% Pelham Media",
            "34,000 hectares that can be legally used for production. There",
        ]],
    )


def write_table_pdf(pdf_path: Path) -> Path:
    """Build a minimal PDF with absolute-positioned text columns that pdfplumber can detect as a table."""
    # Each row is laid out with explicit x/y positioning using Tm operator
    # so pdfplumber's line/text strategy can reconstruct columns.
    rows = [
        ("Scope", "2022", "2023", "2024"),
        ("Scope 1 tCO2e", "12000", "11500", "10800"),
        ("Scope 2 tCO2e", "5400", "5100", "4900"),
        ("Total emissions", "17400", "16600", "15700"),
    ]
    x_positions = [72, 200, 310, 420]
    lines: list[bytes] = [b"BT", b"/F1 10 Tf"]
    y_start = 700
    for r_idx, row in enumerate(rows):
        y = y_start - r_idx * 20
        for c_idx, cell in enumerate(row):
            x = x_positions[c_idx]
            escaped = cell.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            lines.append(f"1 0 0 1 {x} {y} Tm ({escaped}) Tj".encode("ascii"))
    lines.append(b"ET")
    stream = b"\n".join(lines)

    font_obj_num = 5
    page_obj = (
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 " + str(font_obj_num).encode() + b" 0 R >> >> "
        b"/Contents 4 0 R >>"
    )
    content_obj = b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        page_obj,
        content_obj,
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    payload = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(payload))
        payload.extend(f"{idx} 0 obj\n".encode())
        payload.extend(obj)
        payload.extend(b"\nendobj\n")
    xref_offset = len(payload)
    payload.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode())
    payload.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    pdf_path.write_bytes(bytes(payload))
    return pdf_path


@pytest.fixture
def table_pdf(tmp_path: Path) -> Path:
    return write_table_pdf(tmp_path / "table_test.pdf")


@pytest.fixture
def table_like_pdf(tmp_path: Path) -> Path:
    """PDF whose text contains table-like keywords but no actual pdfplumber table."""
    return write_test_pdf(
        tmp_path / "table_like.pdf",
        [[
            "GHG EMISSIONS",
            "total emissions scope 1 tco2 headcount revenue eur million",
            "breakdown by region consumption gwh mwh ratio",
        ]],
    )


@pytest.fixture
def figure_pdf(tmp_path: Path) -> Path:
    """PDF with figure caption blocks to trigger caption-heuristic figure detection."""
    return write_test_pdf(
        tmp_path / "figure_test.pdf",
        [[
            "CLIMATE DATA",
            "Figure 1 Greenhouse gas emissions trend",
            "Graphique 2 Evolution des emissions de CO2",
        ]],
    )


def run_cli(pdf_path: Path, output_dir: Path, document_id: str = "doc_test", overwrite: bool = False):
    command = [
        sys.executable,
        str(SCRIPT_PATH),
        "--pdf-path",
        str(pdf_path),
        "--document-id",
        document_id,
        "--output-dir",
        str(output_dir),
        "--max-pages",
        "1",
    ]
    if overwrite:
        command.append("--overwrite")
    return subprocess.run(command, text=True, capture_output=True, cwd=PROJECT_ROOT)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
