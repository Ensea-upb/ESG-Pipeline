"""Configuration loading for ESGVariableTargetedExtractionV2."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


@dataclass
class EmbeddingConfig:
    enabled: bool = True
    backend: str = "huggingface_local"
    model_name: str = "BAAI/bge-m3"
    local_model_path: str | None = None
    device: str = "auto"
    batch_size: int = 16
    normalize_embeddings: bool = True
    offline_mode: bool = True
    fallback_backend: str = "lexical"


@dataclass
class RetrievalConfig:
    top_k_per_variable: int = 20
    min_retrieval_score: float = 0.25
    embedding_weight: float = 0.60
    keyword_weight: float = 0.25
    unit_weight: float = 0.10
    section_weight: float = 0.05


@dataclass
class ChunkingConfig:
    max_chunk_chars: int = 1200
    overlap_chars: int = 150
    include_page_context: bool = True
    include_table_context: bool = True
    include_visual_context: bool = True


@dataclass
class ExtractionConfig:
    require_quote: bool = True
    require_company: bool = True
    require_fiscal_year: bool = True
    reject_structural_false_positives: bool = True
    reject_iso_standards_as_values: bool = True
    reject_section_numbers_as_values: bool = True
    reject_page_numbers_as_values: bool = True
    reject_footnotes_as_values: bool = True


@dataclass
class OutputConfig:
    write_csv: bool = True
    write_jsonl: bool = True
    schema_version: str = "2.0.0"


@dataclass
class V2Config:
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "V2Config":
        emb = EmbeddingConfig(**{k: v for k, v in data.get("embedding", {}).items()
                                  if k in EmbeddingConfig.__dataclass_fields__})
        ret = RetrievalConfig(**{k: v for k, v in data.get("retrieval", {}).items()
                                  if k in RetrievalConfig.__dataclass_fields__})
        chk = ChunkingConfig(**{k: v for k, v in data.get("chunking", {}).items()
                                 if k in ChunkingConfig.__dataclass_fields__})
        ext = ExtractionConfig(**{k: v for k, v in data.get("extraction", {}).items()
                                   if k in ExtractionConfig.__dataclass_fields__})
        out = OutputConfig(**{k: v for k, v in data.get("output", {}).items()
                               if k in OutputConfig.__dataclass_fields__})
        return cls(embedding=emb, retrieval=ret, chunking=chk, extraction=ext, output=out)


def load_config(config_path: str | Path | None = None) -> V2Config:
    if config_path is None:
        _here = Path(__file__).resolve().parents[2]
        config_path = _here / "config" / "extraction_v2_config.yaml"

    config_path = Path(config_path)
    if not config_path.exists():
        return V2Config()

    if yaml is None:
        return V2Config()

    try:
        with config_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return V2Config.from_dict(data)
    except Exception:
        return V2Config()
