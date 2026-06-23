from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import networkx as nx
import pandas as pd

from .documents import DocumentChunk
from .embeddings import EmbeddingClient, top_k_similar
from .llm import LLMClient


@dataclass
class Triple:
    subject: str
    relation: str
    object: str
    source: str = ""


class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_sources: dict[str, set[str]] = {}

    def add_triple(self, triple: Triple) -> None:
        subject = triple.subject.strip()
        obj = triple.object.strip()
        relation = triple.relation.strip()
        if not subject or not obj or not relation:
            return
        self.graph.add_node(subject)
        self.graph.add_node(obj)
        self.graph.add_edge(subject, obj, relation=relation, source=triple.source)
        self.node_sources.setdefault(subject, set()).add(triple.source)
        self.node_sources.setdefault(obj, set()).add(triple.source)

    def build_from_chunks(
        self,
        chunks: list[DocumentChunk],
        llm: LLMClient,
        max_chunks: int | None = None,
    ) -> list[Triple]:
        triples: list[Triple] = []
        selected = chunks if max_chunks is None else chunks[:max_chunks]
        for chunk in selected:
            extracted = llm.extract_triples(chunk.text)
            for item in extracted:
                triple = Triple(
                    subject=item["subject"],
                    relation=item["relation"],
                    object=item["object"],
                    source=chunk.source,
                )
                triples.append(triple)
                self.add_triple(triple)
        return triples

    def save_xlsx(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for subject, obj, data in self.graph.edges(data=True):
            rows.append(
                {
                    "subject": subject,
                    "relation": data.get("relation", ""),
                    "object": obj,
                    "source": data.get("source", ""),
                }
            )
        pd.DataFrame(rows).to_excel(path, index=False)

    def load_xlsx(self, path: Path) -> bool:
        if not path.exists():
            return False
        frame = pd.read_excel(path)
        self.graph.clear()
        self.node_sources.clear()
        for _, row in frame.iterrows():
            self.add_triple(
                Triple(
                    subject=str(row.get("subject", "")),
                    relation=str(row.get("relation", "")),
                    object=str(row.get("object", "")),
                    source=str(row.get("source", "")),
                )
            )
        return self.graph.number_of_edges() > 0

    def guided_retrieval(
        self,
        query: str,
        embedding_client: EmbeddingClient,
        top_k: int,
        hop_depth: int,
    ) -> str:
        if self.graph.number_of_nodes() == 0:
            return ""

        nodes = list(self.graph.nodes())
        node_vectors = embedding_client.embed(nodes)
        query_vector = embedding_client.embed_one(query)
        seed_indices = top_k_similar(query_vector, node_vectors, min(top_k, len(nodes)))

        visited: set[str] = set()
        lines: list[str] = []
        for seed_index in seed_indices:
            seed = nodes[seed_index]
            self._collect_neighborhood(seed, hop_depth, visited, lines)
        return "\n".join(lines)

    def _collect_neighborhood(self, seed: str, hop_depth: int, visited: set[str], lines: list[str]) -> None:
        frontier = [(seed, 0)]
        while frontier:
            node, depth = frontier.pop(0)
            if node in visited:
                continue
            visited.add(node)
            for _, neighbor, data in self.graph.out_edges(node, data=True):
                relation = data.get("relation", "related to")
                source = data.get("source", "")
                source_note = f" (source: {source})" if source else ""
                lines.append(f"- {node} --[{relation}]--> {neighbor}{source_note}")
                if depth + 1 < hop_depth:
                    frontier.append((neighbor, depth + 1))
            for predecessor, _, data in self.graph.in_edges(node, data=True):
                relation = data.get("relation", "related to")
                source = data.get("source", "")
                source_note = f" (source: {source})" if source else ""
                lines.append(f"- {predecessor} --[{relation}]--> {node}{source_note}")
                if depth + 1 < hop_depth:
                    frontier.append((predecessor, depth + 1))