# KG-RAG AI Tutor

Adaptive AI tutoring system based on **Knowledge Graph-enhanced Retrieval-Augmented Generation (KG-RAG)**.

Paper: *How to build an adaptive AI tutor for any course using KG-RAG* (Dong et al., ICEIT 2025, IEEE).

## Architecture

```
Student query
    │
    ├─► Chat history reuse (MiniLM / embedding similarity ≥ 0.85)
    │
    ├─► RAG: vector similarity over course chunks
    │
    └─► KGR: knowledge-graph traversal for expanded context
              │
              ▼
        DeepSeek-V3 response synthesis
```

### Pipeline (paper Section III)

1. **KG construction** — chunk course PDFs (~1,000 tokens), extract `[Entity, Relation, Entity]` triples with DeepSeek-V3, save to `data/knowledge_graph.xlsx`.
2. **Knowledge-Guided Retrieval** — embed the query, match KG nodes, traverse neighbors for interconnected context.
3. **Response synthesis** — combine similarity context + KG-expanded context and generate the tutoring answer.

## Quick start

```bash
git clone https://github.com/098765d/AI_Tutor.git
cd AI_Tutor
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

Edit `config.yaml` and add your keys:

```yaml
llm:
  api_key: ""          # DeepSeek API key

embeddings:
  api_key: ""          # DashScope API key (optional — falls back to local MiniLM)
```

Run the app:

```bash
streamlit run app.py
```

1. Open the sidebar and click **Build / Rebuild Course Index** (uses PDFs in `pdf/`).
2. Ask questions in the chat box.
3. Switch between **KG-RAG** and **Standard RAG** to compare modes.

## Configuration

| Key | Purpose |
|-----|---------|
| `llm.api_key` | DeepSeek-V3 chat completions |
| `embeddings.api_key` | Alibaba `text-embedding-v2` (paper default) |
| `kg_rag.chunk_size` | PDF chunk size in words |
| `kg_rag.kg_hop_depth` | Graph traversal depth for KGR |
| `kg_rag.chat_history_threshold` | Reuse threshold (default 0.85) |

If DashScope key is empty, embeddings automatically fall back to `sentence-transformers/all-MiniLM-L6-v2`.

## Project layout

```
AI_Tutor/
├── app.py                 # Streamlit UI
├── config.yaml            # API keys (gitignored — copy from config.example.yaml)
├── config.example.yaml
├── pdf/                   # Bundled course materials
├── src/
│   ├── tutor.py           # KG-RAG orchestration
│   ├── knowledge_graph.py # KG build + KGR
│   ├── vector_store.py    # RAG retrieval
│   ├── llm.py             # DeepSeek client
│   ├── embeddings.py      # DashScope / local embeddings
│   ├── documents.py       # PDF loading & chunking
│   ├── chat_history.py    # History reuse (Fig. 6 in paper)
│   └── export.py          # HTML chat export
└── data/                  # Generated index files (gitignored)
```

## References

- [ICEIT 2025 paper (IEEE Xplore)](https://doi.org/10.1109/ICEIT64364.2025.10975937)
- [Assessment quiz used in the study](https://github.com/098765d/KG-RAG/blob/main/MC_quiz.pdf)
- [DeepSeek API](https://platform.deepseek.com/)
- [DashScope embeddings](https://help.aliyun.com/zh/model-studio/developer-reference/text-embedding-synchronous-api)

## License

See [LICENSE](LICENSE).