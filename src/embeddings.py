from __future__ import annotations

import math
from typing import Iterable

import numpy as np

from .config import EmbeddingConfig


class EmbeddingClient:
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self._local_model = None

    @property
    def ready(self) -> bool:
        if self.config.provider == "dashscope":
            return bool(self.config.api_key)
        return True

    def embed(self, texts: Iterable[str]) -> list[list[float]]:
        items = [text.strip() for text in texts if text and text.strip()]
        if not items:
            return []
        if self.config.provider == "dashscope" and self.config.api_key:
            return self._embed_dashscope(items)
        return self._embed_local(items)

    def embed_one(self, text: str) -> list[float]:
        vectors = self.embed([text])
        return vectors[0] if vectors else []

    def _embed_dashscope(self, texts: list[str]) -> list[list[float]]:
        try:
            import dashscope
            from dashscope import TextEmbedding
        except ImportError as exc:
            raise ImportError("Install dashscope: pip install dashscope") from exc

        dashscope.api_key = self.config.api_key
        response = TextEmbedding.call(model=self.config.model, input=texts)
        if response.status_code != 200:
            raise RuntimeError(f"DashScope embedding failed: {response.message}")
        embeddings = response.output["embeddings"]
        embeddings.sort(key=lambda item: item["text_index"])
        return [item["embedding"] for item in embeddings]

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        model = self._get_local_model()
        vectors = model.encode(texts, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]

    def _get_local_model(self):
        if self._local_model is None:
            from sentence_transformers import SentenceTransformer

            self._local_model = SentenceTransformer(self.config.local_model)
        return self._local_model


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def top_k_similar(query_vector: list[float], corpus_vectors: list[list[float]], k: int) -> list[int]:
    if not corpus_vectors:
        return []
    scores = [cosine_similarity(query_vector, vector) for vector in corpus_vectors]
    ranked = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)
    return ranked[:k]