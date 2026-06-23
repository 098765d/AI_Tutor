from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass
class DocumentChunk:
    chunk_id: str
    source: str
    text: str
    page: int | None = None


def list_course_pdfs(*directories: Path) -> list[Path]:
    pdfs: list[Path] = []
    for directory in directories:
        if not directory.exists():
            continue
        pdfs.extend(sorted(directory.glob("*.pdf")))
    return pdfs


def extract_pdf_text(pdf_path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(pdf_path))
    pages: list[tuple[int, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append((index, text))
    return pages


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(words):
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks


def build_chunks_from_pdfs(
    pdf_paths: list[Path],
    chunk_size: int,
    chunk_overlap: int,
) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for pdf_path in pdf_paths:
        for page_number, page_text in extract_pdf_text(pdf_path):
            for index, chunk_text_value in enumerate(
                chunk_text(page_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            ):
                chunk_id = f"{pdf_path.stem}_p{page_number}_c{index}"
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        source=pdf_path.name,
                        text=chunk_text_value,
                        page=page_number,
                    )
                )
    return chunks


def save_chunks(path: Path, chunks: list[DocumentChunk]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "chunk_id": chunk.chunk_id,
            "source": chunk.source,
            "text": chunk.text,
            "page": chunk.page,
        }
        for chunk in chunks
    ]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_chunks(path: Path) -> list[DocumentChunk]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        DocumentChunk(
            chunk_id=item["chunk_id"],
            source=item["source"],
            text=item["text"],
            page=item.get("page"),
        )
        for item in payload
    ]