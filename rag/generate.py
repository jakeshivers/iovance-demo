"""Grounded answer generation with citations and refusal."""
import logging
import sys

from rag.guard import GUARD_RULES, redact, wrap
from rag.interfaces import LLM, AnthropicLLM, OllamaLLM
from rag.retrieve import CFG, cite, rerank, search

log = logging.getLogger("rag")
log.setLevel(logging.INFO)
_handler = logging.FileHandler("rag.log")
_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
log.addHandler(_handler)

REFUSAL = "INSUFFICIENT_CONTEXT"
SYSTEM = f"""You answer questions about FDA regulatory guidance using ONLY the provided context.
Rules:
- Every claim must end with its citation copied exactly from the document's cite attribute, e.g. [doc §section p.page].
- Do not use outside knowledge. Do not invent citations.
- If the context does not answer the question, reply exactly: {REFUSAL}

{GUARD_RULES}"""


def make_llm(name: str | None = None) -> LLM:
    return {"ollama": OllamaLLM, "anthropic": AnthropicLLM}[name or CFG["llm"]]()


def answer(q: str, llm: LLM, mode: str | None = None) -> tuple[str, list[dict]]:
    q = redact(q)
    hits = search(q, mode)
    top = rerank(q, hits, top=1)[0]["score"] if hits else 0.0
    log.info("query=%r mode=%s top_rerank=%.3f cites=%s", q, mode or CFG["retrieval"], top, [cite(h) for h in hits])
    if top < CFG["min_rerank_score"]:
        return REFUSAL, hits
    context = "\n\n".join(wrap(cite(h), h["text"]) for h in hits)
    return llm.complete(SYSTEM, f"Context:\n{context}\n\nQuestion: {q}"), hits


if __name__ == "__main__":
    text, _ = answer(sys.argv[1], make_llm())
    print(text)
