from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .chat_history import ChatHistoryStore
from .config import AppConfig, ensure_data_dirs
from .documents import build_chunks_from_pdfs, list_course_pdfs, save_chunks
from .embeddings import EmbeddingClient
from .knowledge_graph import KnowledgeGraph
from .llm import LLMClient
from .vector_store import VectorStore, format_similarity_context


@dataclass
class TutorResponse:
    answer: str
    mode: str
    reused_history: bool
    similarity_context: str
    expanded_context: str


class KGRAGTutor:
    def __init__(self, config: AppConfig):
        self.config = config
        ensure_data_dirs(config)
        self.llm = LLMClient(config.llm)
        self.embeddings = EmbeddingClient(config.embeddings)
        self.vector_store = VectorStore(self.embeddings)
        self.knowledge_graph = KnowledgeGraph()
        self.history = ChatHistoryStore(
            self.embeddings,
            threshold=config.kg_rag.chat_history_threshold,
        )
        self._loaded = False

    @property
    def is_indexed(self) -> bool:
        return self._loaded and bool(self.vector_store.chunks)

    def load_indexes(self) -> bool:
        vector_loaded = self.vector_store.load(self.config.paths.vector_store)
        self.knowledge_graph.load_xlsx(self.config.paths.knowledge_graph)
        self.history.load(self.config.paths.chat_history)
        self._loaded = vector_loaded
        return vector_loaded

    def build_indexes(
        self,
        extra_pdf_dirs: list[Path] | None = None,
        rebuild_kg: bool = True,
        kg_chunk_limit: int | None = 12,
    ) -> dict[str, int]:
        pdf_dirs = [self.config.paths.pdf_dir, self.config.paths.uploads_dir]
        if extra_pdf_dirs:
            pdf_dirs.extend(extra_pdf_dirs)
        pdf_paths = list_course_pdfs(*pdf_dirs)
        if not pdf_paths:
            raise FileNotFoundError("No PDF course materials found. Add files to pdf/ or upload them.")

        chunks = build_chunks_from_pdfs(
            pdf_paths,
            chunk_size=self.config.kg_rag.chunk_size,
            chunk_overlap=self.config.kg_rag.chunk_overlap,
        )
        save_chunks(self.config.paths.chunks_cache, chunks)

        self.vector_store.build(chunks)
        self.vector_store.save(self.config.paths.vector_store)

        triple_count = 0
        if rebuild_kg:
            self.knowledge_graph = KnowledgeGraph()
            triples = self.knowledge_graph.build_from_chunks(
                chunks,
                llm=self.llm,
                max_chunks=kg_chunk_limit,
            )
            triple_count = len(triples)
            self.knowledge_graph.save_xlsx(self.config.paths.knowledge_graph)

        self._loaded = True
        return {
            "pdf_count": len(pdf_paths),
            "chunk_count": len(chunks),
            "triple_count": triple_count,
            "graph_edges": self.knowledge_graph.graph.number_of_edges(),
        }

    def answer(self, query: str, mode: str | None = None) -> TutorResponse:
        if not self.is_indexed and not self.load_indexes():
            raise RuntimeError("Course index is not built. Run 'Build Course Index' first.")

        selected_mode = mode or self.config.kg_rag.default_mode
        reused = self.history.find_reusable_answer(query)
        if reused:
            return TutorResponse(
                answer=reused,
                mode=selected_mode,
                reused_history=True,
                similarity_context="",
                expanded_context="",
            )

        rag_hits = self.vector_store.search(query, top_k=self.config.kg_rag.rag_top_k)
        similarity_context = format_similarity_context(rag_hits)

        expanded_context = ""
        if selected_mode == "kg_rag":
            expanded_context = self.knowledge_graph.guided_retrieval(
                query=query,
                embedding_client=self.embeddings,
                top_k=self.config.kg_rag.kg_top_k,
                hop_depth=self.config.kg_rag.kg_hop_depth,
            )

        answer = self.llm.synthesize_answer(
            query=query,
            similarity_context=similarity_context,
            expanded_context=expanded_context,
            mode=selected_mode,
        )
        self.history.add(query, answer)
        self.history.save(self.config.paths.chat_history)

        return TutorResponse(
            answer=answer,
            mode=selected_mode,
            reused_history=False,
            similarity_context=similarity_context,
            expanded_context=expanded_context,
        )