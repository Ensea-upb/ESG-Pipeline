"""
table_layout_rebuilder.py — Reconstruct table context to avoid unit/column errors.
Prevents: 27% → 27 tonnes, 101 sites → 101 tonnes, ISO 50001 → 50001.
"""
from __future__ import annotations

import re
from typing import Any

from .input_adapter import DocumentV2Input
from .io_utils import write_jsonl

_UNIT_PATTERN = re.compile(
    r"\b(tCO2e?|ktCO2e?|MtCO2e?|kWh|MWh|GWh|TWh|GJ|TJ|PJ|m3|Mm3|km3|ML|"
    r"hectares?|ha|km2|tonnes?|kt|metric\s+ton|employees?|FTE|people|"
    r"percent|%|EUR|USD|M€|B€|MEUR|BEUR|million|billion|"
    r"sites?|years?|hours?|days?|rate|ratio)\b",
    re.IGNORECASE,
)

_PROBABLE_FOOTNOTE_PAT = re.compile(r"^\s*\(\d\)\s*|^\s*\d\)\s*|^\s*\[\d\]\s*")
_SECTION_NUMBER_PAT = re.compile(r"^\d{1,2}\.\d{1,2}(\.\d{1,2})?$")
_ISO_PAT = re.compile(r"\bISO\s*\d{4,5}\b", re.IGNORECASE)


def _extract_units(text: str) -> list[str]:
    return [m.group() for m in _UNIT_PATTERN.finditer(text)]


def _is_probable_footnote(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) == 1 and stripped.isdigit():
        return True
    return bool(_PROBABLE_FOOTNOTE_PAT.match(stripped))


def _is_section_number(text: str) -> bool:
    return bool(_SECTION_NUMBER_PAT.match(text.strip()))


def _is_iso_standard(text: str) -> bool:
    return bool(_ISO_PAT.search(text))


class TableContextChunk:
    def __init__(
        self,
        table_id: str,
        cell_id: str,
        cell_text: str,
        row_header: str,
        col_header: str,
        table_title: str,
        page_number: str,
        section_context: str,
        document_id: str,
        company: str,
        fiscal_year: str,
        official_doc_type: str,
    ) -> None:
        self.table_id = table_id
        self.cell_id = cell_id
        self.cell_text = cell_text
        self.row_header = row_header
        self.col_header = col_header
        self.table_title = table_title
        self.page_number = page_number
        self.section_context = section_context
        self.document_id = document_id
        self.company = company
        self.fiscal_year = fiscal_year
        self.official_doc_type = official_doc_type

        self.nearby_unit: str = ""
        self.unit_source: str = ""
        self.unit_conflict: bool = False
        self.unit_conflict_reason: str = ""
        self.probable_footnote: bool = False
        self.iso_standard_detected: bool = False
        self.section_number_detected: bool = False
        self.warnings: list[str] = []

        self._analyze()

    def _analyze(self) -> None:
        all_text = " ".join([
            self.cell_text, self.row_header, self.col_header, self.table_title
        ])

        # Detect units in context
        cell_units = _extract_units(self.cell_text)
        col_units = _extract_units(self.col_header)
        row_units = _extract_units(self.row_header)
        title_units = _extract_units(self.table_title)

        # Determine nearby_unit with source and conflict detection
        if cell_units:
            self.nearby_unit = cell_units[0]
            self.unit_source = "cell"
        elif col_units:
            self.nearby_unit = col_units[0]
            self.unit_source = "column_header"
            if row_units and row_units[0].lower() != col_units[0].lower():
                self.unit_conflict = True
                self.unit_conflict_reason = (
                    f"Column says '{col_units[0]}' but row context says '{row_units[0]}'"
                )
                self.warnings.append(self.unit_conflict_reason)
        elif row_units:
            self.nearby_unit = row_units[0]
            self.unit_source = "row_header"
        elif title_units:
            self.nearby_unit = title_units[0]
            self.unit_source = "table_title"
            self.warnings.append(f"Unit '{title_units[0]}' inherited from table title — verify scope")

        # Check for structural false positives in the cell value
        if _is_probable_footnote(self.cell_text):
            self.probable_footnote = True
            self.warnings.append(f"probable_footnote: cell value '{self.cell_text}' looks like a footnote marker")

        if _is_iso_standard(self.cell_text) or _is_iso_standard(all_text):
            self.iso_standard_detected = True
            self.warnings.append(f"iso_standard_detected: '{self.cell_text}' or context contains ISO standard number")

        if _is_section_number(self.cell_text):
            self.section_number_detected = True
            self.warnings.append(f"section_number_detected: '{self.cell_text}' looks like a section number")

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_id": self.table_id,
            "cell_id": self.cell_id,
            "cell_text": self.cell_text,
            "row_header": self.row_header,
            "col_header": self.col_header,
            "table_title": self.table_title,
            "page_number": self.page_number,
            "section_context": self.section_context,
            "document_id": self.document_id,
            "company": self.company,
            "fiscal_year": self.fiscal_year,
            "official_doc_type": self.official_doc_type,
            "nearby_unit": self.nearby_unit,
            "unit_source": self.unit_source,
            "unit_conflict": self.unit_conflict,
            "unit_conflict_reason": self.unit_conflict_reason,
            "probable_footnote": self.probable_footnote,
            "iso_standard_detected": self.iso_standard_detected,
            "section_number_detected": self.section_number_detected,
            "warnings": ";".join(self.warnings),
        }


class TableLayoutRebuilder:
    def __init__(self) -> None:
        pass

    def rebuild(
        self,
        doc: DocumentV2Input,
    ) -> list[dict[str, Any]]:
        """Build table context chunks from document input."""
        # Build table_id → table metadata
        table_meta: dict[str, dict[str, Any]] = {}
        for tbl in doc.table_index:
            tid = tbl.get("table_id", "")
            if tid:
                table_meta[tid] = tbl

        # Group cells by table
        cells_by_table: dict[str, list[dict[str, Any]]] = {}
        for cell in doc.table_cells:
            tid = cell.get("table_id", "")
            if tid:
                cells_by_table.setdefault(tid, []).append(cell)

        results: list[dict[str, Any]] = []
        for table_id, cells in cells_by_table.items():
            meta = table_meta.get(table_id, {})
            page_number = str(meta.get("page_number", cells[0].get("page_number", "") if cells else ""))
            table_title = meta.get("table_title", meta.get("caption", ""))
            section_context = meta.get("section_context", "")

            # Build header maps
            col_headers: dict[int, str] = {}
            row_headers: dict[int, str] = {}
            data_cells: list[dict[str, Any]] = []

            for cell in cells:
                row_idx = int(cell.get("row_index", 0))
                col_idx = int(cell.get("column_index", 0))
                text = (cell.get("normalized_text") or cell.get("text") or "").strip()
                if cell.get("is_header_cell") or row_idx == 0:
                    col_headers[col_idx] = text
                elif col_idx == 0:
                    row_headers[row_idx] = text
                    data_cells.append(cell)
                else:
                    data_cells.append(cell)

            for cell in data_cells:
                row_idx = int(cell.get("row_index", 0))
                col_idx = int(cell.get("column_index", 0))
                cell_text = (cell.get("normalized_text") or cell.get("text") or "").strip()
                if not cell_text:
                    continue
                row_header = row_headers.get(row_idx, "")
                col_header = col_headers.get(col_idx, "")
                cell_id = cell.get("cell_id", f"{table_id}_r{row_idx}_c{col_idx}")

                ctx = TableContextChunk(
                    table_id=table_id,
                    cell_id=cell_id,
                    cell_text=cell_text,
                    row_header=row_header,
                    col_header=col_header,
                    table_title=str(table_title),
                    page_number=page_number,
                    section_context=str(section_context),
                    document_id=doc.document_id,
                    company=doc.company,
                    fiscal_year=doc.fiscal_year,
                    official_doc_type=doc.official_doc_type,
                )
                results.append(ctx.to_dict())

        return results


def write_table_context(findings: list[dict[str, Any]], output_dir) -> None:
    from pathlib import Path
    write_jsonl(Path(output_dir) / "table_context_chunks_v2.jsonl", findings)
