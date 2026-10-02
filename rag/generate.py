"""Grounded answer generation with citations and refusal."""
import sys

from rag.interfaces import LLM, AnthropicLLM, OllamaLLM
from rag.retrieve import CFG, cite, rerank, search

REFUSAL = "INSUFFICIENT_CONTEXT"
SYSTEM = f"""You answer questions about FDA regulatory guidance using ONLY the provided context.
Rules:
- Every claim must end with its citation copied exactly from the context header, e.g. [doc §section p.page].
- Do not use outside knowledge. Do not invent citations.
- If the context does not answer the question, reply exactly: {REFUSAL}"""


def make_llm(name: str | None = None) -> LLM:
    return {"ollama": OllamaLLM, "anthropic": AnthropicLLM}[name or CFG["llm"]]()


def answer(q: str, llm: LLM, mode: str | None = None) -> tuple[str, list[dict]]:
    hits = search(q, mode)
    if not hits or rerank(q, hits, top=1)[0]["score"] < CFG["min_rerank_score"]:
        return REFUSAL, hits
    context = "\n\n".join(f"{cite(h)}\n{h['text']}" for h in hits)
    return llm.complete(SYSTEM, f"Context:\n{context}\n\nQuestion: {q}"), hits


if __name__ == "__main__":
    text, _ = answer(sys.argv[1], make_llm())
    print(text)
