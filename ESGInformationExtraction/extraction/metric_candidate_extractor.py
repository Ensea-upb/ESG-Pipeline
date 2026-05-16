"""
metric_candidate_extractor.py
=============================
Détection de candidats métriques par mots-clés + matching hybride.

STRATÉGIE DE MATCHING (cascade 3 couches) :
  1. FlashText / Aho-Corasick (O(n)) — exact, unicode-normalisé
  2. RapidFuzz WRatio — fuzzy fallback per-metric (seuil 82)
  3. Filtres qualité : plausibilité, digits max, filtre année

IMPORTANT : Ce module produit des CANDIDATS, pas des indicateurs fiables.
Les valeurs extraites doivent être validées avant tout usage analytique.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

# ── Optional fast-match backends ────────────────────────────────────────────
try:
    from flashtext import KeywordProcessor as _FlashKeywordProcessor
    _HAS_FLASHTEXT = True
except ImportError:
    _FlashKeywordProcessor = None   # type: ignore[misc,assignment]
    _HAS_FLASHTEXT = False
    logger.warning("flashtext non disponible — fallback sur substring. `pip install flashtext`")

try:
    from rapidfuzz import process as _rfprocess, fuzz as _rffuzz
    _HAS_RAPIDFUZZ = True
except ImportError:
    _rfprocess = None   # type: ignore[assignment]
    _rffuzz = None      # type: ignore[assignment]
    _HAS_RAPIDFUZZ = False
    logger.warning("rapidfuzz non disponible — fuzzy matching désactivé. `pip install rapidfuzz`")

# Seuil fuzzy : 82 = plus strict pour réduire les faux positifs
_FUZZY_THRESHOLD = 82
# Longueur minimale de ligne pour activer le fuzzy (évite de fuzzy-matcher "Scope 1")
_FUZZY_MIN_LINE_LEN = 12
# Longueur minimale d'un keyword pour le fuzzy (élimine les abbréviations comme "DIS")
_FUZZY_MIN_KW_LEN = 8
# Nombre minimal de tokens d'ancrage qui doivent apparaître pour valider un match fuzzy
# (réduit les faux positifs sur tokens isolés comme "fournisseurs" seul)
_FUZZY_MIN_ANCHOR_OVERLAP = 2


def _load_metric_catalog(catalog_path: Optional[Path] = None) -> dict:
    if catalog_path is None:
        catalog_path = (
            Path(__file__).resolve().parents[1]
            / "config"
            / "metric_catalog_v0.yaml"
        )
    if not catalog_path.exists():
        logger.warning("Catalogue de métriques introuvable : %s", catalog_path)
        return {}
    try:
        return yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        logger.error("Erreur de parsing du catalogue %s : %s", catalog_path, exc)
        return {}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Numeric + unit pattern
# ---------------------------------------------------------------------------
_NUMBER_PATTERN = re.compile(
    r"(?P<value>[\d][\d\s,]*(?:\.\d+)?)\s*"
    r"(?P<unit>"
    r"(?:k|m|g)?tco2e?|co2eq?|gco2e|kgco2e"
    r"|gwh|mwh|kwh|thm|gj|mj|tep|toe"
    r"|hm3|m3|m³"
    r"|(?<!\w)kt(?!\w)|(?<!\w)mt(?!\w)|tonnes?"
    r"|(?<!\w)ha(?!\w)|hectares?|km2|m2"
    r"|heures?|hours?|(?<!\w)fte(?!\w)"
    r"|(?<!\w)ratio(?!\w)"
    r"|%"
    r")?",
    re.IGNORECASE,
)

_YEAR_PATTERN = re.compile(r"\b(?:19[0-9]{2}|20[0-9]{2})\b")

_PLAUSIBILITY_RANGES: dict[str, tuple[float, float]] = {
    "%":       (0,    100),
    "ratio":   (0,  10_000),
    "number":  (0, 500_000_000),
    "tco2e":   (0,  20_000_000_000),
    "ktco2e":  (0,  20_000_000),
    "mtco2e":  (0,  20_000),
    "co2e":    (0,  20_000_000_000),
    "co2eq":   (0,  20_000_000_000),
    "gco2e":   (0,  1e18),
    "kgco2e":  (0,  2e13),
    "gwh":     (0,  100_000_000),
    "mwh":     (0,  100_000_000_000),
    "kwh":     (0,  1e14),
    "gj":      (0,  1e12),
    "mj":      (0,  1e15),
    "tep":     (0,  1e10),
    "toe":     (0,  1e10),
    "m3":      (0,  1e12),
    "m³":      (0,  1e12),
    "hm3":     (0,  1e9),
    "t":       (0,  1e11),
    "kt":      (0,  1e8),
    "mt":      (0,  1e5),
    "tonnes":  (0,  1e11),
    "ha":      (0,  1e9),
    "hectares":(0,  1e9),
    "km2":     (0,  1e9),
    "m2":      (0,  1e12),
    "heures":  (0,  1e12),
    "hours":   (0,  1e12),
    "fte":     (0,  500_000_000),
}

_MAX_VALUE_DIGITS = 15


def _clean_digits(raw_value: str) -> str:
    return re.sub(r"\D", "", raw_value)


def _parse_float(raw_value: str) -> Optional[float]:
    cleaned = raw_value.replace(" ", "").replace(",", ".")
    parts = cleaned.split(".")
    if len(parts) > 2:
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _is_year_like(raw_value: str, raw_unit: str) -> bool:
    if raw_unit:
        return False
    digits = _clean_digits(raw_value)
    if len(digits) != 4:
        return False
    try:
        v = int(digits)
        return 1990 <= v <= 2035
    except ValueError:
        return False


def _is_value_plausible(raw_value: str, raw_unit: str, unit_expected: str) -> bool:
    digits = _clean_digits(raw_value)
    if len(digits) > _MAX_VALUE_DIGITS:
        return False
    unit_key = _normalize(raw_unit) if raw_unit else _normalize(unit_expected)
    if unit_key in _PLAUSIBILITY_RANGES:
        v = _parse_float(raw_value)
        if v is None:
            return False
        lo, hi = _PLAUSIBILITY_RANGES[unit_key]
        if not (lo <= v <= hi):
            return False
    return True


def _extract_value_unit(line: str) -> tuple[str, str]:
    best_value = ""
    best_unit = ""
    best_score = -1

    for m in _NUMBER_PATTERN.finditer(line):
        if not m.group("value"):
            continue
        raw_value = re.sub(r"[\s,]", "", m.group("value"))
        if not raw_value or not re.search(r"\d", raw_value):
            continue
        raw_unit = (m.group("unit") or "").strip()
        digit_count = len(_clean_digits(raw_value))
        if digit_count > _MAX_VALUE_DIGITS:
            continue
        if digit_count < 2 and not raw_unit:
            continue
        score = (10 if raw_unit else 0) + digit_count
        if score > best_score:
            best_value = raw_value
            best_unit = raw_unit
            best_score = score

    return best_value, best_unit


def _detect_year_in_context(line: str, context_lines: list[str]) -> Optional[int]:
    candidates: list[int] = []
    for text in [line] + context_lines:
        for m in _YEAR_PATTERN.finditer(text):
            candidates.append(int(m.group()))
    return max(candidates) if candidates else None


def _confidence_for_match(
    raw_value: str,
    raw_unit: str,
    unit_expected: str,
    found_in_adjacent_line: bool,
    match_type: str = "exact",
) -> float:
    """Confidence scale :
      exact match :   0.30 same-line, 0.25 adjacent
      fuzzy match :   0.20 same-line, 0.15 adjacent
      keyword only:   0.10
    """
    if not raw_value:
        return 0.10
    if match_type == "fuzzy":
        base = 0.15 if found_in_adjacent_line else 0.20
    else:
        base = 0.25 if found_in_adjacent_line else 0.30

    if unit_expected and raw_unit:
        unit_norm    = _normalize(raw_unit)
        expected_norm = _normalize(unit_expected)
        if unit_norm == expected_norm or unit_norm in expected_norm or expected_norm in unit_norm:
            base += 0.05
    return round(base, 2)


# ---------------------------------------------------------------------------
# Index builder — constructs FlashText automaton + per-metric fuzzy structures
# ---------------------------------------------------------------------------
def _build_matchers(
    keyword_map: dict[str, tuple[str, str, str]],
) -> tuple[object | None, dict[str, dict[str, tuple[str, str, str]]], dict[str, set[str]]]:
    """Build (flashtext_processor | None, per_metric_kws, per_metric_anchors).

    per_metric_kws:     {metric_id: {kw_norm: (metric_id, label, unit)}}
    per_metric_anchors: {metric_id: set[str]}  — tokens ≥4 chars per metric

    Per-metric anchors prevent cross-metric fuzzy contamination: a line must
    share ≥ _FUZZY_MIN_ANCHOR_OVERLAP tokens with a specific metric's keywords
    before being fuzzy-matched against that metric. Without this, global anchor
    sets allow unrelated lines to pass the gate and generate false positives.
    """
    per_metric_kws: dict[str, dict[str, tuple[str, str, str]]] = {}
    per_metric_anchors: dict[str, set[str]] = {}

    for kw, payload in keyword_map.items():
        metric_id = payload[0]
        if metric_id not in per_metric_kws:
            per_metric_kws[metric_id] = {}
            per_metric_anchors[metric_id] = set()
        per_metric_kws[metric_id][kw] = payload
        for token in kw.split():
            if len(token) >= 4:
                per_metric_anchors[metric_id].add(token)

    if not _HAS_FLASHTEXT:
        return None, per_metric_kws, per_metric_anchors

    processor = _FlashKeywordProcessor(case_sensitive=False)
    for kw, payload in keyword_map.items():
        processor.add_keyword(kw, payload)
    return processor, per_metric_kws, per_metric_anchors


def _flashtext_match(
    processor: object,
    line_norm: str,
) -> Optional[tuple[str, str, str]]:
    """Return (metric_id, label, unit_expected) from FlashText.

    When multiple keywords match on the same line, select the LONGEST span
    (longer keyword = more specific = preferred). This implements the standard
    Aho-Corasick 'longest match wins' disambiguation rule.
    """
    if processor is None:
        return None
    try:
        hits = processor.extract_keywords(line_norm, span_info=True)
        if not hits:
            return None
        # hits: list of (payload, start, end) — pick longest span
        best_payload, best_len = None, -1
        for payload, start, end in hits:
            span_len = end - start
            if span_len > best_len:
                best_len = span_len
                best_payload = payload
        return best_payload  # (metric_id, label, unit_expected)
    except Exception:
        return None


def _fuzzy_match(
    line_norm: str,
    per_metric_kws: dict[str, dict[str, tuple[str, str, str]]],
    per_metric_anchors: dict[str, set[str]],
) -> Optional[tuple[str, str, str, float]]:
    """Return (metric_id, label, unit_expected, score) or None.

    Per-metric anchor pre-filter: for each metric, the line must share at least
    _FUZZY_MIN_ANCHOR_OVERLAP tokens with THAT metric's keywords before fuzzy
    matching runs against it. This prevents cross-metric contamination where a
    generic token (e.g. 'fournisseurs') triggers matching for unrelated metrics
    (e.g. hazardous_waste) because they share a global anchor-token pool.

    Short keywords (<_FUZZY_MIN_KW_LEN) are excluded from the fuzzy pool to
    avoid spurious matches on abbreviations like 'DIS' or 'ha'.
    """
    if not _HAS_RAPIDFUZZ:
        return None
    if len(line_norm) < _FUZZY_MIN_LINE_LEN:
        return None

    line_tokens = set(line_norm.split())
    best_result: Optional[tuple[str, str, str, float]] = None
    best_score: float = _FUZZY_THRESHOLD

    for metric_id, anchors in per_metric_anchors.items():
        # Per-metric anchor gate: require ≥ _FUZZY_MIN_ANCHOR_OVERLAP shared tokens
        overlap = len(line_tokens.intersection(anchors))
        required = min(_FUZZY_MIN_ANCHOR_OVERLAP, len(anchors))
        if overlap < required:
            continue

        # Only include keywords long enough to avoid abbreviation false positives
        kws = {k: v for k, v in per_metric_kws[metric_id].items()
               if len(k) >= _FUZZY_MIN_KW_LEN}
        if not kws:
            continue

        result = _rfprocess.extractOne(
            line_norm,
            kws.keys(),
            scorer=_rffuzz.WRatio,
            score_cutoff=best_score,
        )
        if result is not None:
            kw, score, _ = result
            if score > best_score:
                best_score = score
                metric_id_hit, label_hit, unit_hit = kws[kw]
                best_result = (metric_id_hit, label_hit, unit_hit, score)

    return best_result


# ---------------------------------------------------------------------------
# Fallback plain substring (when flashtext unavailable)
# ---------------------------------------------------------------------------
def _exact_substring_match(
    line_norm: str,
    keyword_map: dict[str, tuple[str, str, str]],
) -> Optional[tuple[str, str, str]]:
    for kw, payload in keyword_map.items():
        if kw in line_norm:
            return payload
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def extract_metric_candidates(
    pages: list[dict],
    metric_catalog: Optional[dict] = None,
    section_type_filter: Optional[str] = None,
    fiscal_year: Optional[int] = None,
) -> list[dict]:
    """
    Détecte des candidats métriques dans une liste de pages.

    Pipeline de matching (cascade) :
      1. FlashText Aho-Corasick exact match — O(n)
      2. RapidFuzz WRatio per-metric fuzzy — seuil 82
      3. Substring fallback si FlashText absent

    Retourne une liste de dicts :
    {
        metric_id, metric_label, raw_value, raw_unit,
        page_number, context_snippet, confidence,
        year_in_context, is_current_year,
        match_type,           ← "exact" | "fuzzy" | "substring"
        fuzzy_score,          ← score RapidFuzz (si fuzzy), sinon None
        value_rejected_reason ← raison si valeur filtrée
    }
    """
    if metric_catalog is None:
        metric_catalog = _load_metric_catalog()

    # Build normalized keyword_map
    keyword_map: dict[str, tuple[str, str, str]] = {}
    for _category, metrics in metric_catalog.items():
        if not isinstance(metrics, dict):
            continue
        for metric_id, info in metrics.items():
            if not isinstance(info, dict):
                continue
            label = info.get("label_fr") or info.get("label_en") or metric_id
            unit_expected = info.get("unit_expected", "")
            for kw in info.get("keywords_fr", []) + info.get("keywords_en", []):
                norm_kw = _normalize(kw)
                if norm_kw:
                    keyword_map[norm_kw] = (metric_id, label, unit_expected)

    # Build fast matchers
    flashtext_proc, per_metric_kws, per_metric_anchors = _build_matchers(keyword_map)

    results: list[dict] = []
    for page in pages:
        page_number = page.get("page_number", 0)
        text = page.get("text", "")
        lines = text.splitlines()

        for idx, line in enumerate(lines):
            line_norm = _normalize(line)
            if not line_norm:
                continue

            matched_metric_id: Optional[str] = None
            matched_label: Optional[str] = None
            unit_expected: str = ""
            match_type: str = "exact"
            fuzzy_score: Optional[float] = None

            # ── Layer 1 : FlashText (Aho-Corasick O(n)) ──────────────────
            hit = _flashtext_match(flashtext_proc, line_norm)
            if hit:
                matched_metric_id, matched_label, unit_expected = hit
                match_type = "exact"
            else:
                # ── Layer 2 : RapidFuzz per-metric fuzzy ─────────────────
                fuzzy_hit = _fuzzy_match(line_norm, per_metric_kws, per_metric_anchors)
                if fuzzy_hit:
                    matched_metric_id, matched_label, unit_expected, fuzzy_score = fuzzy_hit
                    match_type = "fuzzy"
                elif not _HAS_FLASHTEXT:
                    # ── Layer 3 : substring fallback ──────────────────────
                    sub_hit = _exact_substring_match(line_norm, keyword_map)
                    if sub_hit:
                        matched_metric_id, matched_label, unit_expected = sub_hit
                        match_type = "substring"

            if matched_metric_id is None:
                continue

            # ── Value extraction ──────────────────────────────────────────
            raw_value, raw_unit = _extract_value_unit(line)
            found_in_adjacent = False

            if not raw_value and idx + 1 < len(lines):
                raw_value, raw_unit = _extract_value_unit(lines[idx + 1])
                if raw_value:
                    found_in_adjacent = True

            # ── Quality filters ───────────────────────────────────────────
            value_rejected_reason: Optional[str] = None
            if raw_value:
                if _is_year_like(raw_value, raw_unit):
                    value_rejected_reason = "year_like_value"
                    raw_value = ""
                    raw_unit = ""
                elif not _is_value_plausible(raw_value, raw_unit, unit_expected):
                    value_rejected_reason = "implausible_value"
                    raw_value = ""
                    raw_unit = ""

            confidence = _confidence_for_match(
                raw_value, raw_unit, unit_expected, found_in_adjacent, match_type
            )

            # ── Temporal discrimination (±5 lines) ───────────────────────
            context_lines = []
            for offset in (-3, -2, -1, 1, 2, 3, 4, 5):
                ci = idx + offset
                if 0 <= ci < len(lines):
                    context_lines.append(lines[ci])

            year_in_context = _detect_year_in_context(line, context_lines)
            if fiscal_year is not None and year_in_context is not None:
                is_current_year: Optional[bool] = (year_in_context == fiscal_year)
            else:
                is_current_year = None

            results.append({
                "metric_id":            matched_metric_id,
                "metric_label":         matched_label,
                "raw_value":            raw_value,
                "raw_unit":             raw_unit,
                "page_number":          page_number,
                "context_snippet":      line.strip()[:200],
                "confidence":           confidence,
                "year_in_context":      year_in_context,
                "is_current_year":      is_current_year,
                "match_type":           match_type,
                "fuzzy_score":          fuzzy_score,
                "value_rejected_reason":value_rejected_reason,
            })

    return results
