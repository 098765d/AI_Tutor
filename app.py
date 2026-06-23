from __future__ import annotations

from pathlib import Path

import streamlit as st
from PIL import Image

from src.config import load_config
from src.export import generate_html
from src.tutor import KGRAGTutor

ROOT = Path(__file__).resolve().parent


def get_tutor(deepseek_key: str, dashscope_key: str) -> KGRAGTutor:
    overrides: dict = {}
    if deepseek_key:
        overrides.setdefault("llm", {})["api_key"] = deepseek_key
    if dashscope_key:
        overrides.setdefault("embeddings", {})["api_key"] = dashscope_key

    if "tutor" in st.session_state and not overrides:
        return st.session_state["tutor"]

    config = load_config(overrides=overrides or None)
    if not config.llm.api_key:
        raise ValueError(
            "DeepSeek API key is required. Add llm.api_key to config.yaml or enter it in the sidebar."
        )
    if config.embeddings.provider == "dashscope" and not config.embeddings.api_key:
        merged = {**(overrides or {}), "embeddings": {"provider": "local"}}
        config = load_config(overrides=merged)

    tutor = KGRAGTutor(config)
    tutor.load_indexes()
    return tutor


st.set_page_config(
    page_title="KG-RAG AI Tutor",
    page_icon="🎓",
    layout="wide",
)

logo_path = ROOT / "logo.png"
if logo_path.exists():
    logo = Image.open(logo_path)
else:
    logo = None

header_left, header_right = st.columns([1, 4])
with header_left:
    if logo:
        st.image(logo, width=110)
with header_right:
    st.title("KG-RAG AI Tutor")
    st.caption(
        "Knowledge Graph-enhanced Retrieval-Augmented Generation for adaptive course tutoring "
        "(Dong et al., ICEIT 2025)."
    )

st.markdown(
    """
This implementation follows the KG-RAG architecture:

1. **RAG** retrieves similar course chunks via embeddings.
2. **Knowledge-Guided Retrieval (KGR)** expands context by traversing a course knowledge graph.
3. **DeepSeek-V3** synthesizes a grounded tutoring response from both contexts.

Set API keys in `config.yaml`, or enter them below to override blank values.
"""
)

with st.sidebar:
    st.header("Settings")
    if logo:
        st.image(logo, width=100)

    mode = st.radio(
        "Answering mode",
        options=["kg_rag", "rag"],
        format_func=lambda value: "KG-RAG (recommended)" if value == "kg_rag" else "Standard RAG",
        index=0,
    )

    deepseek_key = st.text_input("DeepSeek API key", type="password")
    dashscope_key = st.text_input("DashScope API key (embeddings)", type="password")

    st.divider()
    st.subheader("Course index")
    rebuild_kg = st.checkbox("Rebuild knowledge graph", value=True)
    kg_chunk_limit = st.slider("KG extraction chunks (API cost control)", 4, 40, 12)

    if st.button("Build / Rebuild Course Index", type="primary"):
        try:
            tutor = get_tutor(deepseek_key, dashscope_key)
            with st.spinner("Indexing PDFs, building vector store and knowledge graph..."):
                stats = tutor.build_indexes(rebuild_kg=rebuild_kg, kg_chunk_limit=kg_chunk_limit)
            st.success(
                f"Indexed {stats['pdf_count']} PDFs · {stats['chunk_count']} chunks · "
                f"{stats['triple_count']} triples · {stats['graph_edges']} graph edges"
            )
            st.session_state["tutor"] = tutor
        except Exception as exc:
            st.error(str(exc))

    if st.button("Download chat history (HTML)"):
        messages = st.session_state.get("messages", [])
        if not messages:
            st.warning("No chat history yet.")
        else:
            html_data = generate_html(messages)
            st.download_button(
                label="Save chat_history.html",
                data=html_data,
                file_name="chat_history.html",
                mime="text/html",
            )

    st.divider()
    st.caption("Paper: How to build an adaptive AI tutor using KG-RAG (ICEIT 2025)")


uploaded_pdfs = st.file_uploader("Upload additional course PDFs", type=["pdf"], accept_multiple_files=True)
if uploaded_pdfs and st.button("Save uploaded PDFs"):
    upload_dir = ROOT / "data" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    for uploaded in uploaded_pdfs:
        target = upload_dir / uploaded.name
        target.write_bytes(uploaded.getbuffer())
    st.success(f"Saved {len(uploaded_pdfs)} file(s) to data/uploads/. Rebuild the index to include them.")


if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="🧑‍🎓" if message["role"] == "user" else "👨🏻‍🏫"):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask the AI tutor a course question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍🎓"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="👨🏻‍🏫"):
        placeholder = st.empty()
        try:
            tutor = get_tutor(deepseek_key, dashscope_key)
            if not tutor.is_indexed:
                tutor.load_indexes()
            with st.spinner("Retrieving context and generating answer..."):
                result = tutor.answer(prompt, mode=mode)
            suffix = ""
            if result.reused_history:
                suffix = "\n\n*Answer reused from chat history (cosine similarity ≥ threshold).*"
            elif mode == "kg_rag":
                suffix = "\n\n*Generated with KG-RAG (similarity retrieval + knowledge-graph expansion).*"
            else:
                suffix = "\n\n*Generated with standard RAG.*"
            placeholder.markdown(result.answer + suffix)
            st.session_state.messages.append({"role": "assistant", "content": result.answer + suffix})
            st.session_state["tutor"] = tutor
        except Exception as exc:
            placeholder.error(str(exc))