"""
constrained_extractor.py — Variable-constrained extraction from retrieval results.
Enforces: anti-ISO, anti-section-number, unit-variable coherence, lineage, quote required.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from .semantic_catalog import SemanticCatalog

_NUMERIC_PAT = re.compile(r"(?<!\w)([-+]?\d{1,3}(?:[,\s]\d{3})*(?:[.,]\d+)?)\s*(%)?(?!\w)")
_YEAR_PAT = re.compile(r"\b(19[89]\d|20[012]\d)\b")
_ISO_PREFIX_PAT = re.compile(r"^ISO\s*(\d{4,5})$", re.IGNORECASE)
_ISO_BARE_PAT = re.compile(r"^\d{4,5}$")
_SECTION_NUMBER_PAT = re.compile(r"^\d{1,2}\.\d{1,2}(\.\d+)?$")
_PAGE_NUMBER_PAT = re.compile(r"^[Pp]age\s+\d+$|^\d{1,4}$")
_FOOTNOTE_PAT = re.compile(r"^\(\d\)$|^\d\)$|^\[\d\]$")

# ISO standard codes commonly referenced in ESG/sustainability reports
_KNOWN_ISO_ESG = frozenset({
    "9001", "14001", "14004", "14006", "14025", "14031",
    "14040", "14044", "14046", "14064", "14067", "14068",
    "20121", "20400", "26000", "37001", "45001", "50001", "55001",
})

_VARIABLE_UNIT_HINTS: dict[str, list[str]] = {
    "co2_emissions": ["tco2", "ktco2", "mtco2", "co2e", "co2"],
    "carbon_intensity": ["tco2", "gco2", "kgco2", "per"],
    "energy_consumption": ["kwh", "mwh", "gwh", "twh", "gj", "tj", "pj"],
    "water_consumption": ["m3", "mm3", "ml", "megalit", "cubic"],
    "waste": ["tonnes", "ton", "kt", "kg"],
    "biodiversity": ["ha", "hectare", "km2", "species", "site"],
    "fossil_exposure": ["%", "percent", "m€", "eur", "usd"],
    "turnover": ["%", "percent", "employee", "fte"],
    "diversity": ["%", "percent", "women", "female", "employee"],
    "work_accidents": ["rate", "per", "%", "accident"],
    "human_capital": ["employee", "fte", "people", "hour", "day", "%"],
    "supply_chain": ["%", "supplier", "site", "m€"],
    "human_rights": ["%", "case", "site"],
    "board_independence": ["%", "director", "member"],
    "ceo_chairman_separation": [],  # qualitative
    "remuneration": ["€", "eur", "usd", "m€", "%", "ratio"],
    "shareholder_rights": ["%", "share"],
    "transparency": [],  # qualitative
    "esg_scandals": [],
    "fraud": [],
    "corruption": [],
    "pollution": [],
    "lawsuits": [],
    "social_controversies": [],
    "market_cap": ["m€", "b€", "meur", "beur", "usd", "billion", "million"],
    "volatility": ["%", "beta"],
    "leverage": ["ratio", "%", "m€"],
    "roa": ["%", "ratio"],
    "roe": ["%", "ratio"],
    "liquidity": ["ratio", "m€", "%"],
    "stock_returns": ["%", "tsr"],
}


def _make_candidate_id(document_id: str, target_variable: str, raw_value: str, page: str) -> str:
    raw = f"{document_id}|{target_variable}|{raw_value}|{page}"
    return "cand_v2_" + hashlib.md5(raw.encode()).hexdigest()[:20]


def _is_iso_standard_value(text: str) -> bool:
    text = text.strip()
    m = _ISO_PREFIX_PAT.match(text)
    if m:
        return True  # Any "ISO NNNNN" prefix pattern is treated as a standard reference
    if _ISO_BARE_PAT.match(text):
        return text in _KNOWN_ISO_ESG
    return False


def _is_section_number(text: str) -> bool:
    return bool(_SECTION_NUMBER_PAT.fullmatch(text.strip()))


def _is_page_number(text: str) -> bool:
    return bool(_PAGE_NUMBER_PAT.fullmatch(text.strip()))


def _is_footnote_marker(text: str) -> bool:
    return bool(_FOOTNOTE_PAT.fullmatch(text.strip()))


def _extract_numeric_values(text: str) -> list[tuple[str, str]]:
    """Return list of (value_str, unit_suffix) from text."""
    results = []
    for m in _NUMERIC_PAT.finditer(text):
        val = m.group(1).replace(",", "").replace(" ", "")
        suffix = m.group(2) or ""
        results.append((val, suffix))
    return results


def _extract_year(text: str) -> str:
    years = _YEAR_PAT.findall(text)
    return years[0] if years else ""


def _extract_unit_from_text(text: str, expected_units: list[str]) -> str:
    text_lower = text.lower()
    # Check longer/more specific units first to avoid "m3" shadowing "Mm3"
    for unit in sorted(expected_units, key=len, reverse=True):
        if unit.lower() in text_lower:
            return unit
    return ""


def _check_unit_coherence(
    raw_unit: str,
    variable: str,
    catalog: SemanticCatalog,
) -> tuple[bool, str]:
    """Returns (is_coherent, reason)."""
    if not raw_unit:
        return True, ""

    forbidden = [u.lower() for u in catalog.get_forbidden_units(variable)]
    if any(f in raw_unit.lower() for f in forbidden if f):
        return False, f"unit '{raw_unit}' is forbidden for {variable}"

    hints = _VARIABLE_UNIT_HINTS.get(variable, [])
    if hints:
        unit_lower = raw_unit.lower()
        matches = [h for h in hints if h in unit_lower]
        if not matches:
            # Still acceptable if expected_units matches
            expected = [u.lower() for u in catalog.get_expected_units(variable)]
            if any(e in unit_lower or unit_lower in e for e in expected):
                return True, ""
            # Unit mismatch but not definitive — flag as warning not rejection
            return True, f"unit '{raw_unit}' is unexpected for {variable} but not forbidden"
    return True, ""


def _build_quote(text: str, max_len: int = 300) -> str:
    """Trim text to a short evidence quote."""
    text = text.strip()
    if len(text) <= max_len:
        return text
    # Try to end at a sentence boundary
    truncated = text[:max_len]
    last_period = max(truncated.rfind("."), truncated.rfind(";"))
    if last_period > max_len // 2:
        return truncated[: last_period + 1]
    return truncated + "…"


class ConstrainedExtractor:
    def __init__(
        self,
        catalog: SemanticCatalog,
        schema_version: str = "2.0.0",
        reject_iso: bool = True,
        reject_section_numbers: bool = True,
        reject_page_numbers: bool = True,
        reject_footnotes: bool = True,
    ) -> None:
        self.catalog = catalog
        self.schema_version = schema_version
        self.reject_iso = reject_iso
        self.reject_section_numbers = reject_section_numbers
        self.reject_page_numbers = reject_page_numbers
        self.reject_footnotes = reject_footnotes

    def extract_from_retrieval(
        self,
        retrieval_results: list[dict[str, Any]],
        chunks_by_id: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for ret in retrieval_results:
            chunk_id = ret.get("chunk_id", "")
            chunk = chunks_by_id.get(chunk_id, {})
            text = chunk.get("text", ret.get("text_snippet", ""))
            if not text:
                continue
            target_variable = ret.get("target_variable", "")
            cands = self._extract_from_chunk(ret, chunk, text, target_variable)
            candidates.extend(cands)
        return candidates

    def _extract_from_chunk(
        self,
        ret: dict[str, Any],
        chunk: dict[str, Any],
        text: str,
        target_variable: str,
    ) -> list[dict[str, Any]]:
        cfg = self.catalog.get_variable_config(target_variable)
        if not cfg:
            return []

        expected_units = self.catalog.get_expected_units(target_variable)
        indicator_family = self.catalog.get_indicator_family(target_variable)
        document_id = ret.get("document_id", chunk.get("document_id", ""))
        company = ret.get("company", chunk.get("company", ""))
        company_slug = chunk.get("company_slug", company)
        company_name = chunk.get("company_name", "")
        fiscal_year = ret.get("fiscal_year", chunk.get("fiscal_year", ""))
        official_doc_type = ret.get("official_doc_type", chunk.get("official_doc_type", ""))
        final_path = chunk.get("final_path", "")
        page_number = ret.get("page_number", chunk.get("page_number", ""))
        source_type = ret.get("source_type", chunk.get("source_type", "paragraph"))
        retrieval_score = float(ret.get("retrieval_score", 0.0))

        is_qualitative = cfg.get("expected_value_type", "") in ("qualitative", "numeric_or_qualitative")

        numeric_pairs = _extract_numeric_values(text)
        unit_from_text = _extract_unit_from_text(text, expected_units)
        raw_year = _extract_year(text)
        quote = _build_quote(text)

        candidates: list[dict[str, Any]] = []

        if numeric_pairs:
            for (val_str, pct_suffix) in numeric_pairs[:3]:  # max 3 per chunk
                raw_value = val_str + pct_suffix if pct_suffix else val_str
                raw_unit = unit_from_text or (pct_suffix if pct_suffix else "")

                status, rejection_reason, warning_flags = self._validate_candidate(
                    raw_value=raw_value,
                    raw_unit=raw_unit,
                    target_variable=target_variable,
                    text=text,
                    retrieval_score=retrieval_score,
                )

                cand = self._build_candidate(
                    document_id=document_id, company=company, company_name=company_name,
                    company_slug=company_slug, fiscal_year=fiscal_year,
                    official_doc_type=official_doc_type, final_path=final_path,
                    page_number=str(page_number), source_type=source_type,
                    target_variable=target_variable, indicator_family=indicator_family,
                    raw_value=raw_value, raw_unit=raw_unit,
                    raw_year=raw_year, quote=quote,
                    chunk=chunk, retrieval_score=retrieval_score,
                    status=status, rejection_reason=rejection_reason,
                    warning_flags=warning_flags,
                )
                candidates.append(cand)
        elif is_qualitative and quote:
            # Qualitative: produce one candidate with no numeric value
            status, rejection_reason, warning_flags = "needs_review", "", ""
            if retrieval_score < self.catalog.get_min_relevance_score(target_variable):
                status = "rejected_low_relevance"
                rejection_reason = f"score {retrieval_score:.2f} below threshold"
            cand = self._build_candidate(
                document_id=document_id, company=company, company_name=company_name,
                company_slug=company_slug, fiscal_year=fiscal_year,
                official_doc_type=official_doc_type, final_path=final_path,
                page_number=str(page_number), source_type=source_type,
                target_variable=target_variable, indicator_family=indicator_family,
                raw_value="", raw_unit="",
                raw_year=raw_year, quote=quote,
                chunk=chunk, retrieval_score=retrieval_score,
                status=status, rejection_reason=rejection_reason,
                warning_flags=warning_flags,
            )
            candidates.append(cand)
        else:
            if quote:
                cand = self._build_candidate(
                    document_id=document_id, company=company, company_name=company_name,
                    company_slug=company_slug, fiscal_year=fiscal_year,
                    official_doc_type=official_doc_type, final_path=final_path,
                    page_number=str(page_number), source_type=source_type,
                    target_variable=target_variable, indicator_family=indicator_family,
                    raw_value="", raw_unit="",
                    raw_year=raw_year, quote=quote,
                    chunk=chunk, retrieval_score=retrieval_score,
                    status="rejected_no_value",
                    rejection_reason="no numeric value found in chunk",
                    warning_flags="",
                )
                candidates.append(cand)

        return candidates

    def _validate_candidate(
        self,
        raw_value: str,
        raw_unit: str,
        target_variable: str,
        text: str,
        retrieval_score: float,
    ) -> tuple[str, str, str]:
        """Returns (status, rejection_reason, warning_flags)."""
        warnings: list[str] = []

        # ISO standard check
        if self.reject_iso and _is_iso_standard_value(raw_value):
            return "rejected_structural_noise", f"ISO standard number: {raw_value}", ""

        # Section number check — skip if a unit is present (e.g. "4.2 Mm3" is a real value)
        if self.reject_section_numbers and _is_section_number(raw_value) and not raw_unit:
            return "rejected_structural_noise", f"section number: {raw_value}", ""

        # Page number check (bare small integers without unit context)
        if self.reject_page_numbers and _is_page_number(raw_value) and not raw_unit:
            return "rejected_structural_noise", f"bare number without unit context: {raw_value}", ""

        # Footnote check
        if self.reject_footnotes and _is_footnote_marker(raw_value):
            return "rejected_structural_noise", f"footnote marker: {raw_value}", ""

        # Employee-unit noise filter
        # — single digit + "employees" → almost certainly a table footnote marker
        # — all-zero value (e.g. "000" from a truncated "102,000" table cell) → reject
        if raw_unit and any(k in raw_unit.lower() for k in ("employee", "fte", "people")):
            clean = raw_value.rstrip("%")
            if re.fullmatch(r"0+", clean):
                return "rejected_structural_noise", f"all-zero value fragment: {raw_value}", ""
            if re.fullmatch(r"\d", clean):  # bare single digit
                return "rejected_structural_noise", f"single-digit value with employee unit (likely footnote): {raw_value}", ""

        # Unit coherence
        coherent, unit_msg = _check_unit_coherence(raw_unit, target_variable, self.catalog)
        if not coherent:
            return "rejected_unit_mismatch", unit_msg, ""
        if unit_msg:
            warnings.append(unit_msg)

        # Score threshold
        min_score = self.catalog.get_min_relevance_score(target_variable)
        if retrieval_score < min_score:
            return "rejected_low_relevance", f"score {retrieval_score:.2f} < {min_score}", ""

        # Variable-specific rules
        var_status = self._apply_variable_rules(raw_value, raw_unit, target_variable)
        if var_status:
            return var_status[0], var_status[1], ";".join(warnings)

        status = "candidate_found" if raw_unit else "needs_review"
        return status, "", ";".join(warnings)

    def _apply_variable_rules(
        self, raw_value: str, raw_unit: str, variable: str
    ) -> tuple[str, str] | None:
        """Variable-specific mapping rules. Returns (status, reason) if rejected, else None."""
        unit_lower = raw_unit.lower()

        # Enforce: Scope 3 + MtCO2e → ghg_emissions (co2_emissions)
        if "mtco2" in unit_lower or "ktco2" in unit_lower or "tco2" in unit_lower:
            if variable not in ("co2_emissions", "carbon_intensity"):
                return ("rejected_unit_mismatch",
                        f"CO2 unit '{raw_unit}' must map to co2_emissions not {variable}")

        # Enforce: water + Mm3/m3 → water_consumption
        if any(u in unit_lower for u in ["mm3", " m3", "megalit", "ml"]):
            if variable not in ("water_consumption",):
                return ("rejected_unit_mismatch",
                        f"Water unit '{raw_unit}' must map to water_consumption not {variable}")

        # Enforce: employees/FTE/people → human_capital
        if any(u in unit_lower for u in ["employee", "fte", "people", "salari"]):
            if variable not in ("human_capital", "turnover", "diversity", "work_accidents",
                                "supply_chain", "human_rights"):
                return ("rejected_unit_mismatch",
                        f"Employee unit '{raw_unit}' cannot map to {variable}")

        return None

    def _build_candidate(
        self,
        document_id: str, company: str, company_name: str, company_slug: str,
        fiscal_year: str, official_doc_type: str, final_path: str,
        page_number: str, source_type: str,
        target_variable: str, indicator_family: str,
        raw_value: str, raw_unit: str, raw_year: str,
        quote: str, chunk: dict[str, Any], retrieval_score: float,
        status: str, rejection_reason: str, warning_flags: str,
    ) -> dict[str, Any]:
        cand_id = _make_candidate_id(document_id, target_variable, raw_value, page_number)
        return {
            "candidate_id": cand_id,
            "schema_version": self.schema_version,
            "engine": "esg_variable_targeted_extraction_v2",
            "target_variable": target_variable,
            "indicator_family": indicator_family,
            "document_id": document_id,
            "company": company,
            "company_name": company_name,
            "company_slug": company_slug,
            "fiscal_year": fiscal_year,
            "official_doc_type": official_doc_type,
            "final_path": final_path,
            "page_number": page_number,
            "chunk_id": chunk.get("chunk_id", ""),
            "source_type": source_type,
            "raw_value": raw_value,
            "raw_unit": raw_unit,
            "normalized_value": raw_value,
            "normalized_unit": raw_unit,
            "raw_year": raw_year,
            "prepared_year": raw_year or fiscal_year,
            "quote": quote,
            "evidence_id": chunk.get("evidence_id", ""),
            "table_id": chunk.get("table_id", ""),
            "figure_id": chunk.get("figure_id", ""),
            "crop_id": chunk.get("crop_id", ""),
            "retrieval_score": round(retrieval_score, 4),
            "extraction_score": 0.0,
            "candidate_score": 0.0,
            "candidate_status": status,
            "rejection_reason": rejection_reason,
            "warning_flags": warning_flags,
            "lineage": f"v2|{source_type}|{chunk.get('chunk_id', '')}",
        }
