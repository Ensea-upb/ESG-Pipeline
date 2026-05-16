from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import pandas as pd

from .scope import filter_dataframe_scope


FAMILY_PRIORITY = {
    "annual_report": 100,
    "sustainability_report": 90,
    "climate_report": 80,
    "governance_report": 70,
    "remuneration_report": 60,
    "vigilance_plan": 50,
    "assurance_report": 45,
    "cdp_response": 40,
    "sbti_commitment": 35,
    "corporate_policy": 30,
    "agm_document": 25,
    "half_year_report": 20,
    "investor_presentation": 15,
    "earnings_call": 10,
}


@dataclass
class CanonicalDocument:
    canonical_document_id: str
    sha256: str

    company_name: Optional[str]
    company_slug: Optional[str]
    fiscal_year: Optional[int]

    canonical_retriever_name: Optional[str]
    canonical_document_family: Optional[str]
    canonical_local_path: Optional[str]
    canonical_manifest_path: Optional[str]
    canonical_source_url: Optional[str]
    canonical_source_title: Optional[str]
    canonical_score: Optional[float]

    document_families_detected: list[str] = field(default_factory=list)
    retrievers_detected: list[str] = field(default_factory=list)
    source_urls_detected: list[str] = field(default_factory=list)
    source_titles_detected: list[str] = field(default_factory=list)

    duplicate_count: int = 1
    is_duplicate_group: bool = False
    all_references: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CanonicalRegistryBuildResult:
    status: str
    message: str

    total_input_documents: int
    total_documents_with_sha256: int
    total_unique_documents: int
    total_duplicate_groups: int
    total_duplicate_documents: int
    total_multi_family_groups: int

    output_json_path: Optional[str] = None
    output_csv_path: Optional[str] = None
    summary_path: Optional[str] = None
    errors: list[dict] = field(default_factory=list)


class CanonicalRegistryBuilder:
    """
    Construit un registre canonique avec un seul document par SHA-256 unique.

    Le builder ne modifie pas les PDF ni les manifests. Il lit uniquement le
    registre central produit par DocumentRegistryBuilder.
    """

    def __init__(
        self,
        registry_csv_path: str | Path = "data/central_registry/documents_registry.csv",
        output_dir: str | Path = "data/deduplication",
        company_slugs: set[str] | None = None,
        years: set[int] | None = None,
    ) -> None:
        self.registry_csv_path = Path(registry_csv_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.company_slugs = company_slugs
        self.years = years

    def build(self) -> CanonicalRegistryBuildResult:
        if not self.registry_csv_path.exists():
            raise FileNotFoundError(
                f"Registre central introuvable : {self.registry_csv_path}"
            )

        df = pd.read_csv(self.registry_csv_path)
        self.validate_columns(df)
        df = filter_dataframe_scope(df, self.company_slugs, self.years)

        total_input_documents = len(df)
        df_with_sha = df[
            df["sha256"].notna()
            & (df["sha256"].astype(str).str.strip() != "")
        ].copy()
        total_documents_with_sha256 = len(df_with_sha)

        canonical_documents: list[CanonicalDocument] = []
        errors: list[dict] = []

        for sha256, group in df_with_sha.groupby("sha256", dropna=True, sort=True):
            try:
                canonical_documents.append(
                    self.build_canonical_document(sha256=str(sha256), group=group)
                )
            except Exception as exc:
                errors.append({"sha256": str(sha256), "error": str(exc)})

        output_json_path = self.output_dir / "canonical_documents.json"
        output_csv_path = self.output_dir / "canonical_documents.csv"
        summary_path = self.output_dir / "canonical_registry_summary.json"

        self.save_json(canonical_documents, output_json_path)
        self.save_csv(canonical_documents, output_csv_path)

        duplicate_groups = [
            document for document in canonical_documents if document.is_duplicate_group
        ]
        total_duplicate_documents = sum(
            document.duplicate_count for document in duplicate_groups
        )
        total_multi_family_groups = sum(
            1
            for document in duplicate_groups
            if len(document.document_families_detected) > 1
        )

        status = "success" if not errors else "completed_with_errors"
        result = CanonicalRegistryBuildResult(
            status=status,
            message=(
                f"Registre canonique construit : {len(canonical_documents)} "
                f"document(s) unique(s), {len(duplicate_groups)} groupe(s) "
                f"de doublons exacts."
            ),
            total_input_documents=total_input_documents,
            total_documents_with_sha256=total_documents_with_sha256,
            total_unique_documents=len(canonical_documents),
            total_duplicate_groups=len(duplicate_groups),
            total_duplicate_documents=total_duplicate_documents,
            total_multi_family_groups=total_multi_family_groups,
            output_json_path=str(output_json_path),
            output_csv_path=str(output_csv_path),
            summary_path=str(summary_path),
            errors=errors,
        )

        summary_path.write_text(
            json.dumps(asdict(result), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return result

    def build_canonical_document(
        self,
        sha256: str,
        group: pd.DataFrame,
    ) -> CanonicalDocument:
        group = group.copy()
        group["_original_order"] = range(len(group))
        group["_score_sort"] = group["score"].apply(self.score_sort_value)
        group["_family_priority"] = group["document_family"].apply(
            self.family_priority
        )
        group["_candidate_rank_sort"] = group["candidate_rank"].apply(
            self.rank_sort_value
        )
        group["_official_source_sort"] = group.apply(
            self.official_source_sort_value,
            axis=1,
        )
        group["_local_path_length"] = group["local_path"].apply(
            lambda value: len(str(value)) if self.has_value(value) else 10**9
        )

        ranked = group.sort_values(
            by=[
                "_score_sort",
                "_family_priority",
                "_candidate_rank_sort",
                "_official_source_sort",
                "_local_path_length",
                "_original_order",
            ],
            ascending=[False, False, True, False, True, True],
            kind="mergesort",
        )

        canonical = ranked.iloc[0]
        references = [self.row_to_reference(row) for _, row in group.iterrows()]
        families = self.unique_values(group["document_family"].tolist())
        retrievers = self.unique_values(group["retriever_name"].tolist())
        source_urls = self.unique_values(group["source_url"].tolist())
        source_titles = self.unique_values(group["source_title"].tolist())

        return CanonicalDocument(
            canonical_document_id=self.build_canonical_document_id(sha256),
            sha256=sha256,
            company_name=self.safe_value(canonical.get("company_name")),
            company_slug=self.safe_value(canonical.get("company_slug")),
            fiscal_year=self.safe_int_or_none(canonical.get("fiscal_year")),
            canonical_retriever_name=self.safe_value(
                canonical.get("retriever_name")
            ),
            canonical_document_family=self.safe_value(
                canonical.get("document_family")
            ),
            canonical_local_path=self.safe_value(canonical.get("local_path")),
            canonical_manifest_path=self.safe_value(canonical.get("manifest_path")),
            canonical_source_url=self.safe_value(canonical.get("source_url")),
            canonical_source_title=self.safe_value(canonical.get("source_title")),
            canonical_score=self.safe_float_or_none(canonical.get("score")),
            document_families_detected=families,
            retrievers_detected=retrievers,
            source_urls_detected=source_urls,
            source_titles_detected=source_titles,
            duplicate_count=len(group),
            is_duplicate_group=len(group) > 1,
            all_references=references,
        )

    @staticmethod
    def validate_columns(df: pd.DataFrame) -> None:
        required_columns = {
            "document_id",
            "retriever_name",
            "document_family",
            "company_name",
            "company_slug",
            "fiscal_year",
            "source_url",
            "source_title",
            "local_path",
            "manifest_path",
            "sha256",
            "score",
            "candidate_rank",
        }

        missing = sorted(required_columns - set(df.columns))
        if missing:
            raise ValueError(
                "Colonnes absentes du registre central : " + ", ".join(missing)
            )

    @staticmethod
    def build_canonical_document_id(sha256: str) -> str:
        digest = hashlib.sha256(f"canonical|{sha256}".encode("utf-8")).hexdigest()
        return f"canonical_{digest[:24]}"

    @staticmethod
    def family_priority(value: Any) -> int:
        if not CanonicalRegistryBuilder.has_value(value):
            return 0
        return FAMILY_PRIORITY.get(str(value), 0)

    @staticmethod
    def score_sort_value(value: Any) -> float:
        if not CanonicalRegistryBuilder.has_value(value):
            return float("-inf")

        try:
            return float(value)
        except (TypeError, ValueError):
            return float("-inf")

    @staticmethod
    def rank_sort_value(value: Any) -> int:
        if not CanonicalRegistryBuilder.has_value(value):
            return 10**9

        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 10**9

    @staticmethod
    def official_source_sort_value(row: pd.Series) -> int:
        """
        Heuristique prudente : le registre central ne contient pas le domaine
        officiel. On valorise seulement les URLs dont le domaine contient le
        slug société normalisé.
        """

        source_url = row.get("source_url")
        company_slug = row.get("company_slug")

        if not (
            CanonicalRegistryBuilder.has_value(source_url)
            and CanonicalRegistryBuilder.has_value(company_slug)
        ):
            return 0

        netloc = urlparse(str(source_url)).netloc.lower()
        compact_netloc = netloc.replace("-", "").replace(".", "")
        compact_slug = str(company_slug).lower().replace("-", "")

        if compact_slug and compact_slug in compact_netloc:
            return 1

        return 0

    @staticmethod
    def row_to_reference(row: pd.Series) -> dict:
        fields = [
            "document_id",
            "retriever_name",
            "document_family",
            "company_name",
            "company_slug",
            "fiscal_year",
            "source_url",
            "source_title",
            "source_name",
            "score",
            "decision",
            "local_path",
            "manifest_path",
            "file_size_mb",
            "document_type",
            "storage_role",
            "candidate_rank",
            "stored_at",
            "source_manifest_path",
        ]

        return {
            field: CanonicalRegistryBuilder.safe_value(row.get(field))
            for field in fields
        }

    @staticmethod
    def unique_values(values: list[Any]) -> list[str]:
        seen = set()
        result = []

        for value in values:
            if not CanonicalRegistryBuilder.has_value(value):
                continue

            normalized = str(value)
            if normalized in seen:
                continue

            seen.add(normalized)
            result.append(normalized)

        return result

    @staticmethod
    def save_json(
        documents: list[CanonicalDocument],
        output_path: Path,
    ) -> None:
        payload = [document.to_dict() for document in documents]
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def save_csv(
        documents: list[CanonicalDocument],
        output_path: Path,
    ) -> None:
        rows = []

        for document in documents:
            row = document.to_dict()
            for field_name in [
                "document_families_detected",
                "retrievers_detected",
                "source_urls_detected",
                "source_titles_detected",
                "all_references",
            ]:
                row[field_name] = json.dumps(
                    row.get(field_name) or [],
                    ensure_ascii=False,
                )
            rows.append(row)

        pd.DataFrame(rows).to_csv(output_path, index=False, encoding="utf-8-sig")

    @staticmethod
    def has_value(value: Any) -> bool:
        if value is None:
            return False

        try:
            if pd.isna(value):
                return False
        except (TypeError, ValueError):
            pass

        return str(value).strip() != ""

    @staticmethod
    def safe_value(value: Any):
        if not CanonicalRegistryBuilder.has_value(value):
            return None

        if isinstance(value, float) and value.is_integer():
            return int(value)

        return value

    @staticmethod
    def safe_int_or_none(value: Any) -> Optional[int]:
        if not CanonicalRegistryBuilder.has_value(value):
            return None

        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def safe_float_or_none(value: Any) -> Optional[float]:
        if not CanonicalRegistryBuilder.has_value(value):
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None
