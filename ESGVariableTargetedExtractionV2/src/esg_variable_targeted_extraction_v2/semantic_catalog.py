"""Loads and queries the variable semantic catalog (31 ESG target variables)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

_DEFAULT_CATALOG = Path(__file__).resolve().parents[2] / "config" / "variable_semantic_catalog_v1.yaml"

EXPECTED_VARIABLE_COUNT = 31


class SemanticCatalog:
    def __init__(self, catalog_path: str | Path | None = None) -> None:
        path = Path(catalog_path) if catalog_path else _DEFAULT_CATALOG
        self._data: dict[str, dict[str, Any]] = {}
        self._load(path)

    def _load(self, path: Path) -> None:
        if not path.exists():
            return
        if yaml is None:
            return
        try:
            with path.open(encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            self._data = {k: v for k, v in raw.items() if isinstance(v, dict)}
        except Exception:
            self._data = {}

    def list_variables(self) -> list[str]:
        return sorted(self._data.keys())

    def get_variable_config(self, variable: str) -> dict[str, Any]:
        return self._data.get(variable, {})

    def get_all_query_terms(self, variable: str) -> list[str]:
        cfg = self.get_variable_config(variable)
        terms: list[str] = []
        terms.extend(cfg.get("query_terms_en", []))
        terms.extend(cfg.get("query_terms_fr", []))
        return terms

    def get_positive_patterns(self, variable: str) -> list[str]:
        return self.get_variable_config(variable).get("positive_patterns", [])

    def get_negative_patterns(self, variable: str) -> list[str]:
        return self.get_variable_config(variable).get("negative_patterns", [])

    def get_expected_units(self, variable: str) -> list[str]:
        return self.get_variable_config(variable).get("expected_units", [])

    def get_forbidden_units(self, variable: str) -> list[str]:
        return self.get_variable_config(variable).get("forbidden_units", [])

    def get_structural_fp_patterns(self, variable: str) -> list[str]:
        return self.get_variable_config(variable).get("structural_false_positive_patterns", [])

    def get_domain(self, variable: str) -> str:
        return self.get_variable_config(variable).get("domain", "unknown")

    def get_indicator_family(self, variable: str) -> str:
        domain = self.get_domain(variable)
        return {
            "environmental": "environmental",
            "social": "social",
            "governance": "governance",
            "controversy": "controversy",
            "financial": "financial",
        }.get(domain, "unknown")

    def get_min_relevance_score(self, variable: str) -> float:
        return float(self.get_variable_config(variable).get("minimum_relevance_score", 0.25))

    def get_preferred_doc_types(self, variable: str) -> list[str]:
        return self.get_variable_config(variable).get("preferred_doc_types", [])

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, variable: str) -> bool:
        return variable in self._data
