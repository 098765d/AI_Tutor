from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .embeddings import EmbeddingClient, cosine_similarity


@dataclass
class HistoryEntry:
    question: str
    answer: str
    vector: list[float]


class ChatHistoryStore:
    def __init__(self, embedding_client: EmbeddingClient, threshold: float = 0.85):
        self.embedding_client = embedding_client
        self.threshold = threshold
        self.entries: list[HistoryEntry] = []

    def find_reusable_answer(self, query: str) -> str | None:
        if not self.entries:
            return None
        query_vector = self.embedding_client.embed_one(query)
        best_score = 0.0
        best_answer = None
        for entry in self.entries:
            score = cosine_similarity(query_vector, entry.vector)
            if score > best_score:
                best_score = score
                best_answer = entry.answer
        if best_score >= self.threshold and best_answer:
            return best_answer
        return None

    def add(self, question: str, answer: str) -> None:
        vector = self.embedding_client.embed_one(question)
        self.entries.append(HistoryEntry(question=question, answer=answer, vector=vector))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {"question": entry.question, "answer": entry.answer, "vector": entry.vector}
            for entry in self.entries
        ]
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def load(self, path: Path) -> None:
        if not path.exists():
            self.entries = []
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.entries = [
            HistoryEntry(
                question=item["question"],
                answer=item["answer"],
                vector=item["vector"],
            )
            for item in payload
        ]