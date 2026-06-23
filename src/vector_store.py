from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .documents import DocumentChunk
from .embeddings import EmbeddingClient, cosine_similarity, top_k_similar


@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    score: float


class VectorStore:
    def __init__(self, embedding_client: EmbeddingClient):
        self.embedding_client = embedding_client
        self.chunks: list[DocumentChunk] = []
        self.vectors: list[list[float]] = []

    def build(self, chunks: list[DocumentChunk]) -> None:
        self.chunks = chunks
        self.vectors = self.embedding_client.embed(chunk.text for chunk in chunks)

    def search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        if not self.chunks or not self.vectors:
            return []
        query_vector = self.embedding_client.embed_one(query)
        indices = top_k_similar(query_vector, self.vectors, top_k)
        results: list[RetrievedChunk] = []
        for index in indices:
            results.append(
                RetrievedChunk(
                    chunk=self.chunks[index],
                    score=cosine_similarity(query_vector, self.vectors[index]),
                )
            )
        return results

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "source": chunk.source,
                    "text": chunk.text,
                    "page": chunk.page,
                }
                for chunk in self.chunks
            ],
            "vectors": self.vectors,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def load(self, path: Path) -> bool:
        if not path.exists():
            return False
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.chunks = [
            DocumentChunk(
                chunk_id=item["chunk_id"],
                source=item["source"],
                text=item["text"],
                page=item.get("page"),
            )
            for item in payload.get("chunks", [])
        ]
        self.vectors = payload.get("vectors", [])
        return bool(self.chunks and self.vectors)


def format_similarity_context(results: list[RetrievedChunk]) -> str:
    if not results:
        return ""
    blocks: list[str] = []
    for rank, result in enumerate(results, start=1):
        page = f", page {result.chunk.page}" if result.chunk.page else ""
        blocks.append(
            f"[{rank}] Source: {result.chunk.source}{page}\n{result.chunk.text}"
        )
    return "\n\n".join(blocks)