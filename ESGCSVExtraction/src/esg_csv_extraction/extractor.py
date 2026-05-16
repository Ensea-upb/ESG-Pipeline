from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


CANDIDATE_FIELDS = [
    "document_id",
    "company",
    "fiscal_year",
    "information_type",
    "esg_category",
    "label",
    "raw_value",
    "raw_unit",
    "year",
    "source_modality",
    "page_number",
    "section_id",
    "evidence_id",
    "quote",
    "confidence",
    "review_required",
    "extraction_status",
    "metric_key",
    "metric_label",
    "normalized_value",
    "normalized_unit",
    "reported_year",
    "boundary",
    "segment",
    "geography",
    "methodology",
    "value_kind",
    "target_key",
    "target_label",
    "target_value",
    "target_unit",
    "target_year",
    "baseline_value",
    "baseline_year",
    "metric_related",
    "target_status",
    "policy_topic",
    "policy_type",
    "claim",
    "related_standard",
    "commitment_strength",
    "risk_topic",
    "risk_category",
    "risk_description",
    "affected_area",
    "risk_driver",
    "boundary_type",
    "boundary_value",
    "applies_to_metric",
    "inclusion_exclusion",
    "standard_or_method",
    "methodology_type",
    "applies_to_topic",
]

AUDIT_FIELDS = ["check_name", "status", "message", "count"]
TYPED_CSV_FILES = {
    "observed_metric": "observed_metrics.csv",
    "target": "targets.csv",
    "policy_or_commitment": "policies.csv",
    "risk_statement": "risks.csv",
    "boundary_context": "boundary_contexts.csv",
    "methodology_context": "methodology_contexts.csv",
    "visual_evidence": "visual_evidences.csv",
}
OUTPUT_FILES = (
    "esg_information_candidates.csv",
    "esg_information_candidates.jsonl",
    "observed_metrics.csv",
    "targets.csv",
    "policies.csv",
    "risks.csv",
    "boundary_contexts.csv",
    "methodology_contexts.csv",
    "visual_evidences.csv",
    "extraction_audit.csv",
    "candidate_audit_summary.json",
    "candidate_audit_findings.jsonl",
    "candidate_audit_samples.csv",
    "extraction_summary.json",
)
AUDIT_SAMPLE_FIELDS = [
    "audit_check",
    "document_id",
    "information_type",
    "evidence_id",
    "page_number",
    "confidence",
    "raw_value",
    "raw_unit",
    "year",
    "quote",
]

YEAR_RE = re.compile(r"\b(20[0-4]\d|19[8-9]\d)\b")
NUMBER_UNIT_RE = re.compile(
    r"(?P<value>\b-?\d{1,3}(?:[,\s]\d{3})+(?:\.\d+)?|\b-?\d+(?:\.\d+)?)\s*"
    r"(?P<unit>%|percent|percentage|tonnes?|tons?|tco2e|co2e|kt|mt|kg|mwh|gwh|kwh|m3|"
    r"cubic meters?|hectares?|employees?|fte|hours?|eur millions?|€ millions?|million euros?)?",
    re.IGNORECASE,
)
BASELINE_RE = re.compile(r"\b(?:baseline|base year|reference year)\D{0,40}(20[0-4]\d|19[8-9]\d)\b", re.IGNORECASE)

KEYWORDS = {
    "target": [
        "target", "targets", "goal", "objective", "aim", "commitment to reduce",
        "net zero", "net-zero", "by 2030", "by 2040", "by 2050", "science-based",
    ],
    "policy_or_commitment": [
        "policy", "commitment", "committed", "code of conduct", "human rights",
        "anti-corruption", "supplier code", "due diligence", "vigilance plan",
    ],
    "risk_statement": [
        "risk", "risks", "exposure", "uncertainty", "litigation", "controversy",
        "compliance risk", "climate risk", "transition risk",
    ],
    "boundary_context": [
        "scope", "boundary", "perimeter", "perimetre", "consolidated", "group",
        "subsidiaries", "coverage", "included", "excluded",
    ],
    "methodology_context": [
        "methodology", "method", "calculated", "calculation", "reported in accordance",
        "standard", "protocol", "ghg protocol", "esrs", "tcfd", "assumption",
    ],
}

CATEGORY_KEYWORDS = [
    ("emissions", ["emission", "co2", "co2e", "greenhouse gas", "ghg", "carbon"]),
    ("climate", ["climate", "transition", "net zero", "tcfd"]),
    ("energy", ["energy", "electricity", "mwh", "gwh", "renewable"]),
    ("water", ["water", "withdrawal", "cubic meter", "m3"]),
    ("waste", ["waste", "recycling", "recycled"]),
    ("biodiversity", ["biodiversity", "nature", "hectare", "forest"]),
    ("workforce", ["employee", "workforce", "fte", "headcount"]),
    ("diversity", ["diversity", "women", "gender", "dei", "inclusion"]),
    ("health_safety", ["safety", "accident", "injury", "fatality"]),
    ("human_rights", ["human rights", "due diligence", "vigilance"]),
    ("governance", ["governance", "board", "director"]),
    ("ethics", ["ethics", "code of conduct", "anti-corruption", "corruption"]),
]


@dataclass
class CSVExtractionResult:
    candidates_count: int
    output_dir: Path
    summary: dict[str, Any]


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_audit_findings(path: Path, rows: list[dict[str, Any]]) -> None:
    write_jsonl(path, rows)


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


_CORPUS_DIR_NAMES = {"ESGFinalCorpus", "ESGCorpus", "ESGCorpusTaxonomy", "corpus"}


def infer_company_year(document_id: str, inventory: dict[str, Any], summary: dict[str, Any]) -> tuple[str, str]:
    path_text = str(inventory.get("pdf_path") or summary.get("pdf_path") or "")
    parts = [part for part in re.split(r"[\\/]+", path_text) if part]
    for corpus_name in _CORPUS_DIR_NAMES:
        if corpus_name in parts:
            idx = parts.index(corpus_name)
            if len(parts) > idx + 2:
                return parts[idx + 1], parts[idx + 2]
    match = re.search(r"([a-z0-9][a-z0-9-]*)[_-](20\d{2})", document_id, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2)
    year_match = re.search(r"(20\d{2})", document_id)
    if year_match:
        company_slug = document_id[:year_match.start()].strip("-_").lower() or ""
        return company_slug, year_match.group(1)
    return "", ""


def detect_year(text: str, fallback: str) -> str:
    match = YEAR_RE.search(text)
    return match.group(1) if match else fallback


def detect_category(text: str) -> str:
    lower = text.lower()
    best_category = "general"
    best_count = 0
    for category, keywords in CATEGORY_KEYWORDS:
        count = sum(1 for kw in keywords if kw in lower)
        if count > best_count:
            best_category = category
            best_count = count
    return best_category


def first_metric(text: str) -> tuple[str, str]:
    for match in NUMBER_UNIT_RE.finditer(text):
        value = normalize_text(match.group("value"))
        unit = normalize_text(match.group("unit"))
        normalized_value = value.replace(",", "").replace(" ", "").lstrip("-")
        if not value:
            continue
        if normalized_value.isdigit() and 1000 <= int(normalized_value) <= 2099 and not unit:
            continue
        if normalized_value.isdigit() and int(normalized_value) <= 10 and not unit:
            continue
        if value:
            return value, unit
    return "", ""


def normalized_number(value: str) -> str:
    cleaned = value.replace(" ", "").replace(",", "")
    try:
        return str(float(cleaned)) if "." in cleaned else str(int(cleaned))
    except ValueError:
        return ""


def normalize_unit(unit: str) -> str:
    lower = unit.lower().strip()
    mapping = {
        "percent": "%",
        "percentage": "%",
        "tons": "tonnes",
        "ton": "tonnes",
        "tco2e": "tCO2e",
        "co2e": "tCO2e",
        "gwh": "GWh",
        "mwh": "MWh",
        "kwh": "kWh",
        "m3": "m3",
        "cubic meters": "m3",
        "cubic meter": "m3",
        "employees": "employees",
        "fte": "FTE",
        "hour": "hours",
        "hours": "hours",
        "eur millions": "EUR millions",
        "€ millions": "EUR millions",
        "million euros": "EUR millions",
    }
    return mapping.get(lower, unit)


def metric_key_for(text: str) -> str:
    category = detect_category(text)
    lower = text.lower()
    if "scope 1" in lower:
        return "scope_1_emissions"
    if "scope 2" in lower:
        return "scope_2_emissions"
    if "scope 3" in lower:
        return "scope_3_emissions"
    if category != "general":
        return category
    if "revenue" in lower:
        return "revenue"
    return "unknown_metric"


def is_target_like(text: str) -> bool:
    return has_keyword(text, "target") or bool(re.search(r"\bby\s+20[0-4]\d\b", text, re.IGNORECASE))


def target_year(text: str) -> str:
    by_year = re.search(r"\bby\s+(20[0-4]\d)\b", text, re.IGNORECASE)
    if by_year:
        return by_year.group(1)
    years = YEAR_RE.findall(text)
    return years[-1] if years else ""


def baseline_year(text: str) -> str:
    match = BASELINE_RE.search(text)
    return match.group(1) if match else ""


def standard_or_method(text: str) -> str:
    lower = text.lower()
    for token, label in [
        ("ghg protocol", "GHG Protocol"),
        ("esrs", "ESRS"),
        ("gri", "GRI"),
        ("tcfd", "TCFD"),
        ("limited assurance", "limited assurance"),
        ("reasonable assurance", "reasonable assurance"),
        ("market-based", "market-based"),
        ("location-based", "location-based"),
    ]:
        if token in lower:
            return label
    return ""


def geography(text: str) -> str:
    lower = text.lower()
    for token in ["france", "europe", "asia", "united states", "china", "japan"]:
        if token in lower:
            return token.title()
    return ""


def boundary_value(text: str) -> str:
    lower = text.lower()
    if "group" in lower:
        return "Group"
    if "scope 1" in lower:
        return "Scope 1"
    if "scope 2" in lower:
        return "Scope 2"
    if "scope 3" in lower:
        return "Scope 3"
    return geography(text)


_NEGATION_RE = re.compile(
    r"\b(?:no|not|non|none|without|aucun|aucune|sans|pas de|pas d[''e]|ne pas|never|jamais)\b",
    re.IGNORECASE,
)


def has_keyword(text: str, group: str) -> bool:
    """Return True if any keyword from group is present, excluding negated occurrences.

    Checks a 60-char window before each keyword match for negation signals
    ("no target", "not committed", "sans objectif", etc.).
    """
    lower = text.lower()
    for keyword in KEYWORDS[group]:
        idx = lower.find(keyword)
        while idx != -1:
            window_start = max(0, idx - 60)
            window = lower[window_start:idx]
            if not _NEGATION_RE.search(window):
                return True
            idx = lower.find(keyword, idx + 1)
    return False


def candidate_confidence(evidence: dict[str, Any], base: float) -> float:
    confidence = base
    if evidence.get("review_required"):
        confidence -= 0.08
    if evidence.get("is_quarantined_evidence"):
        confidence -= 0.15
    if evidence.get("downstream_use_policy") == "eligible_for_future_extraction":
        confidence += 0.05
    return round(max(0.05, min(0.6, confidence)), 2)


class ESGCSVExtractor:
    """Conservative candidate extractor from documentary evidence outputs."""

    def __init__(self, input_dir: Path, output_dir: Path, overwrite: bool = False) -> None:
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.overwrite = overwrite

    def run(self) -> CSVExtractionResult:
        self._validate_write_safety()
        started_at = utcnow()
        inventory = read_json(self.input_dir / "document_inventory.json")
        summary_source = read_json(self.input_dir / "extraction_summary.json")
        evidences = read_jsonl(self.input_dir / "multimodal_evidence_index.jsonl")
        audit_rows = self._build_audit_rows(inventory, summary_source, evidences)

        document_id = str(
            inventory.get("document_id")
            or summary_source.get("document_id")
            or self.input_dir.name
        )
        company, fiscal_year = infer_company_year(document_id, inventory, summary_source)
        candidates = self._extract_candidates(evidences, document_id, company, fiscal_year)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        write_csv(self.output_dir / "esg_information_candidates.csv", candidates, CANDIDATE_FIELDS)
        write_jsonl(self.output_dir / "esg_information_candidates.jsonl", candidates)
        typed_counts = self._write_typed_csvs(candidates)
        write_csv(self.output_dir / "extraction_audit.csv", audit_rows, AUDIT_FIELDS)
        candidate_audit = self._build_candidate_audit(candidates)
        write_json(self.output_dir / "candidate_audit_summary.json", candidate_audit["summary"])
        write_audit_findings(self.output_dir / "candidate_audit_findings.jsonl", candidate_audit["findings"])
        write_csv(self.output_dir / "candidate_audit_samples.csv", candidate_audit["samples"], AUDIT_SAMPLE_FIELDS)

        distribution = dict(Counter(row["information_type"] for row in candidates))
        extraction_summary = {
            "schema_version": "0.1.0",
            "module": "ESGCSVExtraction",
            "input_dir": str(self.input_dir.resolve()),
            "output_dir": str(self.output_dir.resolve()),
            "document_id": document_id,
            "company": company,
            "fiscal_year": fiscal_year,
            "started_at": started_at,
            "finished_at": utcnow(),
            "status": "success",
            "source_evidences_count": len(evidences),
            "candidates_count": len(candidates),
            "information_type_distribution": distribution,
            "typed_csv_counts": typed_counts,
            "review_required_count": len(candidates),
            "candidate_only": True,
            "candidate_audit_findings_count": len(candidate_audit["findings"]),
            "candidate_audit_warning_count": sum(1 for item in candidate_audit["findings"] if item["severity"] == "warning"),
            "candidate_audit_error_count": sum(1 for item in candidate_audit["findings"] if item["severity"] == "error"),
            "outputs": list(OUTPUT_FILES),
            "warnings": [
                "All rows are candidate_only and require review.",
                "No ESG indicator is validated by this module.",
            ],
        }
        write_json(self.output_dir / "extraction_summary.json", extraction_summary)
        return CSVExtractionResult(len(candidates), self.output_dir, extraction_summary)

    def _write_typed_csvs(self, candidates: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for information_type, file_name in TYPED_CSV_FILES.items():
            rows = [row for row in candidates if row.get("information_type") == information_type]
            write_csv(self.output_dir / file_name, rows, CANDIDATE_FIELDS)
            counts[file_name] = len(rows)
        return counts

    def _build_candidate_audit(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        distribution = dict(Counter(row["information_type"] for row in candidates))
        source_modality_distribution = dict(Counter(row.get("source_modality", "") for row in candidates))
        duplicate_keys = Counter(
            (
                row.get("evidence_id", ""),
                row.get("information_type", ""),
                row.get("label", ""),
            )
            for row in candidates
        )
        duplicate_rows = [
            row for row in candidates
            if duplicate_keys[(row.get("evidence_id", ""), row.get("information_type", ""), row.get("label", ""))] > 1
        ]
        checks = {
            "candidates_without_quote": [
                row for row in candidates if not normalize_text(row.get("quote"))
            ],
            "observed_metric_without_value": [
                row for row in candidates
                if row.get("information_type") == "observed_metric" and not normalize_text(row.get("raw_value"))
            ],
            "observed_metric_without_unit": [
                row for row in candidates
                if row.get("information_type") == "observed_metric" and not normalize_text(row.get("raw_unit"))
            ],
            "target_without_target_year": [
                row for row in candidates
                if row.get("information_type") == "target" and not normalize_text(row.get("target_year"))
            ],
            "visual_evidence_low_confidence": [
                row for row in candidates
                if row.get("information_type") == "visual_evidence" and float(row.get("confidence") or 0) < 0.25
            ],
            "confidence_above_0_6": [
                row for row in candidates if float(row.get("confidence") or 0) > 0.6
            ],
            "review_required_missing_or_false": [
                row for row in candidates if row.get("review_required") is not True
            ],
            "duplicate_evidence_type_label": duplicate_rows,
            "ineligible_evidence_candidates": [],
        }

        findings: list[dict[str, Any]] = []
        samples: list[dict[str, Any]] = []
        for index, (check_name, rows) in enumerate(checks.items(), start=1):
            count = len(rows)
            severity = "info" if count == 0 else "warning"
            if check_name in {"candidates_without_quote", "confidence_above_0_6", "review_required_missing_or_false"} and count:
                severity = "error"
            findings.append({
                "schema_version": "0.1.0",
                "finding_id": f"candidate_audit_{index:04d}",
                "check_name": check_name,
                "severity": severity,
                "status": "pass" if count == 0 else "needs_review",
                "message": self._audit_message(check_name, count),
                "count": count,
            })
            for row in rows[:10]:
                samples.append({
                    "audit_check": check_name,
                    "document_id": row.get("document_id", ""),
                    "information_type": row.get("information_type", ""),
                    "evidence_id": row.get("evidence_id", ""),
                    "page_number": row.get("page_number", ""),
                    "confidence": row.get("confidence", ""),
                    "raw_value": row.get("raw_value", ""),
                    "raw_unit": row.get("raw_unit", ""),
                    "year": row.get("year", ""),
                    "quote": normalize_text(row.get("quote"))[:400],
                })

        summary = {
            "schema_version": "0.1.0",
            "generated_at": utcnow(),
            "candidates_count": len(candidates),
            "information_type_distribution": distribution,
            "source_modality_distribution": source_modality_distribution,
            "checks_count": len(checks),
            "findings_count": len(findings),
            "warnings_count": sum(1 for item in findings if item["severity"] == "warning"),
            "errors_count": sum(1 for item in findings if item["severity"] == "error"),
            "candidate_only": True,
            "review_required_policy": "all candidates must have review_required=true",
            "checks": {name: len(rows) for name, rows in checks.items()},
        }
        return {"summary": summary, "findings": findings, "samples": samples}

    def _audit_message(self, check_name: str, count: int) -> str:
        if count == 0:
            return f"{check_name}: no issue detected."
        return {
            "candidates_without_quote": f"{count} candidate(s) have an empty quote.",
            "observed_metric_without_value": f"{count} observed_metric candidate(s) have no raw_value.",
            "observed_metric_without_unit": f"{count} observed_metric candidate(s) have no raw_unit.",
            "target_without_target_year": f"{count} target candidate(s) have no target year in the year field.",
            "visual_evidence_low_confidence": f"{count} visual_evidence candidate(s) have confidence below 0.25.",
            "confidence_above_0_6": f"{count} candidate(s) have confidence above the v0.1 ceiling of 0.6.",
            "review_required_missing_or_false": f"{count} candidate(s) are not marked review_required=true.",
            "duplicate_evidence_type_label": f"{count} duplicate candidate row(s) share evidence_id, information_type, and label.",
            "ineligible_evidence_candidates": f"{count} candidate(s) were created from ineligible documentary evidence.",
        }.get(check_name, f"{count} candidate(s) require review for {check_name}.")

    def _validate_write_safety(self) -> None:
        if not self.input_dir.exists() or not self.input_dir.is_dir():
            raise FileNotFoundError(f"input-dir does not exist: {self.input_dir}")
        existing = [name for name in OUTPUT_FILES if (self.output_dir / name).exists()]
        if existing and not self.overwrite:
            raise FileExistsError(
                "Output files already exist. Use --overwrite to replace: " + ", ".join(existing)
            )

    def _build_audit_rows(
        self,
        inventory: dict[str, Any],
        summary: dict[str, Any],
        evidences: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {
                "check_name": "document_inventory_loaded",
                "status": "pass" if inventory else "warning",
                "message": "document_inventory.json was loaded." if inventory else "document_inventory.json is missing or empty.",
                "count": 1 if inventory else 0,
            },
            {
                "check_name": "extraction_summary_loaded",
                "status": "pass" if summary else "warning",
                "message": "extraction_summary.json was loaded." if summary else "extraction_summary.json is missing or empty.",
                "count": 1 if summary else 0,
            },
            {
                "check_name": "multimodal_evidence_loaded",
                "status": "pass" if evidences else "warning",
                "message": "multimodal_evidence_index.jsonl records loaded.",
                "count": len(evidences),
            },
            {
                "check_name": "candidate_policy",
                "status": "pass",
                "message": "All extracted rows are candidate_only and review_required=true.",
                "count": 1,
            },
        ]

    def _extract_candidates(
        self,
        evidences: list[dict[str, Any]],
        document_id: str,
        company: str,
        fiscal_year: str,
    ) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for evidence in evidences:
            if evidence.get("is_quarantined_evidence") or evidence.get("evidence_policy") == "quarantine":
                continue
            if evidence.get("downstream_use_policy") == "exclude_from_automatic_extraction":
                continue
            quote = normalize_text(evidence.get("quote"))
            if not quote:
                continue
            for candidate in self._candidates_for_evidence(evidence, quote, document_id, company, fiscal_year):
                candidates.append(candidate)
        return candidates

    def _base_candidate(
        self,
        evidence: dict[str, Any],
        quote: str,
        document_id: str,
        company: str,
        fiscal_year: str,
        information_type: str,
        label: str,
        confidence: float,
        raw_value: str = "",
        raw_unit: str = "",
    ) -> dict[str, Any]:
        return {
            "document_id": document_id,
            "company": company,
            "fiscal_year": fiscal_year,
            "information_type": information_type,
            "esg_category": detect_category(quote),
            "label": label,
            "raw_value": raw_value,
            "raw_unit": raw_unit,
            "year": detect_year(quote, fiscal_year),
            "source_modality": evidence.get("source_modality", ""),
            "page_number": evidence.get("page_number", ""),
            "section_id": evidence.get("section_id", ""),
            "evidence_id": evidence.get("evidence_id", ""),
            "quote": quote[:1000],
            "confidence": confidence,
            "review_required": True,
            "extraction_status": "candidate_only",
            "metric_key": "",
            "metric_label": "",
            "normalized_value": "",
            "normalized_unit": "",
            "reported_year": "",
            "boundary": "",
            "segment": "",
            "geography": "",
            "methodology": "",
            "value_kind": "",
            "target_key": "",
            "target_label": "",
            "target_value": "",
            "target_unit": "",
            "target_year": "",
            "baseline_value": "",
            "baseline_year": "",
            "metric_related": "",
            "target_status": "",
            "policy_topic": "",
            "policy_type": "",
            "claim": "",
            "related_standard": "",
            "commitment_strength": "",
            "risk_topic": "",
            "risk_category": "",
            "risk_description": "",
            "affected_area": "",
            "risk_driver": "",
            "boundary_type": "",
            "boundary_value": "",
            "applies_to_metric": "",
            "inclusion_exclusion": "",
            "standard_or_method": "",
            "methodology_type": "",
            "applies_to_topic": "",
        }

    def _candidates_for_evidence(
        self,
        evidence: dict[str, Any],
        quote: str,
        document_id: str,
        company: str,
        fiscal_year: str,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        modality = str(evidence.get("source_modality") or "")
        evidence_type = str(evidence.get("evidence_type") or "")
        if modality in {"table", "figure"} or evidence_type in {"table", "figure"}:
            rows.append(self._base_candidate(
                evidence,
                quote,
                document_id,
                company,
                fiscal_year,
                "visual_evidence",
                f"{modality or evidence_type} documentary evidence",
                candidate_confidence(evidence, 0.3),
            ))

        value, unit = first_metric(quote)
        if value and not is_target_like(quote) and (unit or any(word in quote.lower() for word in ["revenue", "emission", "energy", "water", "waste", "employee", "scope"])):
            row = self._base_candidate(
                evidence,
                quote,
                document_id,
                company,
                fiscal_year,
                "observed_metric",
                "numeric value mentioned in documentary evidence",
                candidate_confidence(evidence, 0.42),
                value,
                unit,
            )
            row.update({
                "metric_key": metric_key_for(quote),
                "metric_label": "Observed metric candidate",
                "normalized_value": normalized_number(value),
                "normalized_unit": normalize_unit(unit),
                "reported_year": detect_year(quote, fiscal_year),
                "boundary": boundary_value(quote),
                "geography": geography(quote),
                "methodology": standard_or_method(quote),
                "value_kind": "actual" if unit else "unknown",
            })
            rows.append(row)

        for information_type, label in [
            ("target", "target or objective statement"),
            ("policy_or_commitment", "policy or commitment statement"),
            ("risk_statement", "risk-related statement"),
            ("boundary_context", "boundary or reporting scope context"),
            ("methodology_context", "methodology or reporting standard context"),
        ]:
            if has_keyword(quote, information_type):
                row = self._base_candidate(
                    evidence,
                    quote,
                    document_id,
                    company,
                    fiscal_year,
                    information_type,
                    label,
                    candidate_confidence(evidence, 0.38),
                )
                if information_type == "target":
                    target_value, target_unit = first_metric(quote)
                    row.update({
                        "target_key": metric_key_for(quote),
                        "target_label": "Target candidate",
                        "target_value": target_value,
                        "target_unit": normalize_unit(target_unit),
                        "target_year": target_year(quote),
                        "baseline_year": baseline_year(quote),
                        "metric_related": metric_key_for(quote),
                        "target_status": "candidate_only",
                    })
                elif information_type == "policy_or_commitment":
                    row.update({
                        "policy_topic": detect_category(quote),
                        "policy_type": "commitment" if "commit" in quote.lower() else "policy",
                        "claim": quote[:500],
                        "related_standard": standard_or_method(quote),
                        "commitment_strength": "candidate",
                    })
                elif information_type == "risk_statement":
                    row.update({
                        "risk_topic": detect_category(quote),
                        "risk_category": "transition" if "transition" in quote.lower() else "general",
                        "risk_description": quote[:500],
                        "affected_area": geography(quote),
                        "risk_driver": "climate" if "climate" in quote.lower() else "",
                    })
                elif information_type == "boundary_context":
                    row.update({
                        "boundary_type": "scope" if "scope" in quote.lower() else "organizational",
                        "boundary_value": boundary_value(quote),
                        "applies_to_metric": metric_key_for(quote),
                        "geography": geography(quote),
                        "inclusion_exclusion": "excluded" if "exclud" in quote.lower() else ("included" if "includ" in quote.lower() else ""),
                    })
                elif information_type == "methodology_context":
                    row.update({
                        "standard_or_method": standard_or_method(quote),
                        "methodology_type": "assurance" if "assurance" in quote.lower() else "reporting_method",
                        "applies_to_metric": metric_key_for(quote),
                        "applies_to_topic": detect_category(quote),
                    })
                rows.append(row)
        return rows
