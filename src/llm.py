from __future__ import annotations

import json
import re
from openai import OpenAI

from .config import LLMConfig

KG_EXTRACTION_PROMPT = """Extract entities and relationships from the following course text.
Return ONLY a JSON array of triples, each triple as:
{{"subject": "Entity1", "relation": "Relationship", "object": "Entity2"}}

Rules:
- Use concise, pedagogically meaningful entity names.
- Relations should be verbs or short verb phrases (e.g., "affects", "is a type of").
- Include only relationships explicitly supported by the text.
- Return [] if no clear relationships exist.

Text:
{text}
"""

SYNTHESIS_SYSTEM_PROMPT = """You are an adaptive AI tutor grounded in verified course materials.
Explain concepts clearly, preserve conceptual relationships, and stay faithful to the retrieved context.
If the context is insufficient, say what is missing instead of inventing facts."""


class LLMClient:
    def __init__(self, config: LLMConfig):
        if not config.api_key:
            raise ValueError("LLM API key is missing. Set llm.api_key in config.yaml.")
        self.config = config
        self.client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    def complete(self, user_prompt: str, system_prompt: str | None = None, temperature: float = 0.2) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    def extract_triples(self, text: str) -> list[dict[str, str]]:
        prompt = KG_EXTRACTION_PROMPT.format(text=text[:6000])
        raw = self.complete(prompt, temperature=0.0)
        return _parse_triples(raw)

    def synthesize_answer(
        self,
        query: str,
        similarity_context: str,
        expanded_context: str,
        mode: str,
    ) -> str:
        sections = []
        if similarity_context.strip():
            sections.append(f"Similarity-retrieved course material:\n{similarity_context}")
        if expanded_context.strip() and mode == "kg_rag":
            sections.append(f"Knowledge-graph expanded context:\n{expanded_context}")
        context_block = "\n\n".join(sections) if sections else "No retrieved context available."

        user_prompt = (
            f"Using the following course material:\n{context_block}\n\n"
            f"Please answer the student's question: {query}\n\n"
            "Explain concepts step by step, preserve relationships between ideas, "
            "and cite which themes from the material you relied on."
        )
        return self.complete(user_prompt, system_prompt=SYNTHESIS_SYSTEM_PROMPT)


def _parse_triples(raw: str) -> list[dict[str, str]]:
    raw = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw, re.DOTALL)
    candidate = fenced.group(1) if fenced else raw
    start = candidate.find("[")
    end = candidate.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        data = json.loads(candidate[start : end + 1])
    except json.JSONDecodeError:
        return []

    triples: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        subject = str(item.get("subject", "")).strip()
        relation = str(item.get("relation", "")).strip()
        obj = str(item.get("object", "")).strip()
        if subject and relation and obj:
            triples.append({"subject": subject, "relation": relation, "object": obj})
    return triples