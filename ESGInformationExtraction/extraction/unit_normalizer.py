"""
unit_normalizer.py
==================
Normalise les unités brutes extraites en unités canoniques.

Backend principal : quantulum3 (290+ unités, désambiguïsation par embeddings).
Fallback : dictionnaire de règles manuelles pour les unités ESG non couvertes.

quantulum3 : pip install quantulum3
Source : https://pypi.org/project/quantulum3/
"""

from __future__ import annotations

import logging
import re
from typing import Optional

log = logging.getLogger(__name__)


def _try_import_quantulum():
    try:
        from quantulum3 import parser as qparser
        return qparser
    except ImportError:
        return None


_CO2_UNITS = {
    "tco2e": ("tCO2e", 1.0),
    "tco2": ("tCO2e", 1.0),
    "ktco2e": ("tCO2e", 1_000.0),
    "ktco2": ("tCO2e", 1_000.0),
    "mtco2e": ("tCO2e", 1_000_000.0),
    "mtco2": ("tCO2e", 1_000_000.0),
    "tonnes": ("tCO2e", 1.0),
    "t": ("tCO2e", 1.0),
}

_ENERGY_UNITS = {
    "kwh": ("MWh", 0.001),
    "mwh": ("MWh", 1.0),
    "gwh": ("MWh", 1_000.0),
    "thm": ("MWh", 0.029307),
    "gj": ("MWh", 0.27778),
    "mj": ("MWh", 0.00027778),
}

_PERCENT_UNITS = {"%": ("%", 1.0)}


def _clean_raw_value(raw_value: str) -> Optional[float]:
    """Parse a raw string into a float, handling spaces and commas."""
    if not raw_value:
        return None
    cleaned = raw_value.replace(" ", "").replace("\xa0", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_unit(
    raw_value: str,
    raw_unit: str,
    metric_id: Optional[str] = None,
) -> dict:
    """Normalise une valeur brute et son unité.

    Essaie quantulum3 en premier (290+ unités, désambiguïsation sémantique),
    puis fallback sur le dictionnaire de règles manuelles.

    Retourne un dict :
    {
        "normalized_value": float | None,
        "canonical_unit": str | None,
        "conversion_factor": float | None,
        "normalization_status": "ok" | "unknown_unit" | "parse_error" | "no_value",
        "normalization_backend": "quantulum3" | "rules",
    }
    """
    numeric_value = _clean_raw_value(raw_value)

    if numeric_value is None:
        return {
            "normalized_value": None,
            "canonical_unit": None,
            "conversion_factor": None,
            "normalization_status": "no_value",
            "normalization_backend": "rules",
        }

    # ── Tentative quantulum3 ──────────────────────────────────────────────
    if raw_unit:
        q3_result = _normalize_via_quantulum3(numeric_value, raw_unit)
        if q3_result is not None:
            return q3_result

    # ── Fallback : dictionnaire de règles ESG ────────────────────────────
    return _normalize_via_rules(numeric_value, raw_unit)


def _normalize_via_quantulum3(numeric_value: float, raw_unit: str) -> Optional[dict]:
    """Tente la normalisation via quantulum3. Retourne None en cas d'échec."""
    qparser = _try_import_quantulum()
    if qparser is None:
        return None
    try:
        # On parse la chaîne "1 <unit>" pour extraire l'unité canonique
        quants = qparser.parse(f"1 {raw_unit}")
        if not quants:
            return None
        q = quants[0]
        entity_name = q.unit.entity.name if q.unit and q.unit.entity else ""
        unit_name = q.unit.name if q.unit else raw_unit

        # Mapper les entités quantulum3 vers les canoniques ESG
        canonical, factor = _quantulum_to_esg_canonical(entity_name, unit_name, raw_unit)
        if canonical is None:
            return None

        return {
            "normalized_value": round(numeric_value * factor, 6),
            "canonical_unit": canonical,
            "conversion_factor": factor,
            "normalization_status": "ok",
            "normalization_backend": "quantulum3",
        }
    except Exception as exc:
        log.debug("quantulum3 a échoué pour l'unité '%s' : %s", raw_unit, exc)
        return None


def _quantulum_to_esg_canonical(entity_name: str, unit_name: str, raw_unit: str) -> tuple[Optional[str], float]:
    """Convertit une entité quantulum3 en unité canonique ESG."""
    entity_lower = entity_name.lower()
    unit_lower = unit_name.lower()
    raw_lower = raw_unit.lower().strip()

    # GHG — toujours prioritaire sur masse générique
    if any(tok in raw_lower for tok in ("co2e", "co2eq", "tco2", "ghg")):
        multipliers = {"kt": 1_000.0, "mt": 1_000_000.0, "gt": 1_000_000_000.0, "t": 1.0, "kg": 0.001}
        for prefix, factor in multipliers.items():
            if raw_lower.startswith(prefix):
                return "tCO2e", factor
        return "tCO2e", 1.0

    # Énergie
    if "energy" in entity_lower or any(u in unit_lower for u in ("watt", "wh", "joule")):
        energy_map = {
            "kwh": ("MWh", 0.001),
            "mwh": ("MWh", 1.0),
            "gwh": ("MWh", 1_000.0),
            "twh": ("MWh", 1_000_000.0),
            "gj": ("MWh", 0.27778),
            "mj": ("MWh", 0.00027778),
            "tj": ("MWh", 277.78),
            "tep": ("MWh", 11.63),
            "toe": ("MWh", 11.63),
        }
        for key, (canonical, factor) in energy_map.items():
            if key in raw_lower:
                return canonical, factor

    # Volume / eau
    if "volume" in entity_lower or "litre" in entity_lower or "liter" in entity_lower:
        vol_map = {"hm3": ("m3", 1_000_000.0), "km3": ("m3", 1_000_000_000.0), "l": ("m3", 0.001)}
        for key, (canonical, factor) in vol_map.items():
            if raw_lower == key:
                return canonical, factor
        if "m3" in raw_lower or "m³" in raw_lower:
            return "m3", 1.0

    # Masse générique (déchets)
    if "mass" in entity_lower or "tonne" in unit_lower or "ton" in unit_lower:
        mass_map = {"kt": ("tonnes", 1_000.0), "mt": ("tonnes", 1_000_000.0), "t": ("tonnes", 1.0), "kg": ("tonnes", 0.001)}
        for key, (canonical, factor) in mass_map.items():
            if raw_lower == key:
                return canonical, factor

    # Pourcentage
    if "dimensionless" in entity_lower or "%" in raw_unit:
        return "%", 1.0

    return None, 1.0


def _normalize_via_rules(numeric_value: float, raw_unit: str) -> dict:
    """Fallback : normalisation par dictionnaire de règles ESG."""
    unit_key = raw_unit.lower().strip() if raw_unit else ""

    for lookup in (_CO2_UNITS, _ENERGY_UNITS, _PERCENT_UNITS):
        if unit_key in lookup:
            canonical, factor = lookup[unit_key]
            return {
                "normalized_value": round(numeric_value * factor, 6),
                "canonical_unit": canonical,
                "conversion_factor": factor,
                "normalization_status": "ok",
                "normalization_backend": "rules",
            }

    if unit_key == "":
        return {
            "normalized_value": numeric_value,
            "canonical_unit": None,
            "conversion_factor": None,
            "normalization_status": "ok",
            "normalization_backend": "rules",
        }

    return {
        "normalized_value": None,
        "canonical_unit": None,
        "conversion_factor": None,
        "normalization_status": "unknown_unit",
        "normalization_backend": "rules",
    }
