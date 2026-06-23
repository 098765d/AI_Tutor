from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class LLMConfig:
    provider: str
    api_key: str
    base_url: str
    model: str


@dataclass
class EmbeddingConfig:
    provider: str
    api_key: str
    model: str
    local_model: str


@dataclass
class KGRagConfig:
    chunk_size: int
    chunk_overlap: int
    rag_top_k: int
    kg_top_k: int
    kg_hop_depth: int
    default_mode: str
    chat_history_threshold: float


@dataclass
class PathConfig:
    pdf_dir: Path
    data_dir: Path
    uploads_dir: Path

    @property
    def vector_store(self) -> Path:
        return self.data_dir / "vector_store.json"

    @property
    def knowledge_graph(self) -> Path:
        return self.data_dir / "knowledge_graph.xlsx"

    @property
    def chat_history(self) -> Path:
        return self.data_dir / "chat_history.json"

    @property
    def chunks_cache(self) -> Path:
        return self.data_dir / "chunks.json"


@dataclass
class AppConfig:
    llm: LLMConfig
    embeddings: EmbeddingConfig
    kg_rag: KGRagConfig
    paths: PathConfig


def _resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def load_config(path: Path | None = None, overrides: dict[str, Any] | None = None) -> AppConfig:
    config_path = path or ROOT / "config.yaml"
    if not config_path.exists():
        example = ROOT / "config.example.yaml"
        if example.exists():
            config_path = example
        else:
            raise FileNotFoundError(
                f"No config found. Create {ROOT / 'config.yaml'} from config.example.yaml"
            )

    with config_path.open(encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}

    if overrides:
        raw = _deep_merge(raw, overrides)

    paths_raw = raw.get("paths", {})
    data_dir = _resolve_path(paths_raw.get("data_dir", "data"))

    return AppConfig(
        llm=LLMConfig(**raw.get("llm", {})),
        embeddings=EmbeddingConfig(**raw.get("embeddings", {})),
        kg_rag=KGRagConfig(**raw.get("kg_rag", {})),
        paths=PathConfig(
            pdf_dir=_resolve_path(paths_raw.get("pdf_dir", "pdf")),
            data_dir=data_dir,
            uploads_dir=_resolve_path(paths_raw.get("uploads_dir", str(data_dir / "uploads"))),
        ),
    )


def ensure_data_dirs(config: AppConfig) -> None:
    config.paths.data_dir.mkdir(parents=True, exist_ok=True)
    config.paths.uploads_dir.mkdir(parents=True, exist_ok=True)


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged