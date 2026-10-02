"""BM25, vector, hand-written RRF, and cross-encoder rerank."""
import sys
from functools import cache

import yaml
from sentence_transformers import CrossEncoder

from rag.interfaces import BgeEmbedder, OpenSearchStore

CFG = yaml.safe_load(open("config.yaml"))


@cache
def _store():
    return OpenSearchStore()


@cache
def _embedder():
    return BgeEmbedder()


@cache
def _reranker():
    return CrossEncoder("BAAI/bge-reranker-base")


def bm25(q: str, k: int) -> list[dict]:
    return _store().bm25(q, k)


def vector(q: str, k: int) -> list[dict]:
    return _store().knn(_embedder().embed([q], query=True)[0], k)


def rrf(lists: list[list[dict]], k: int = 60) -> list[dict]:
    """Reciprocal rank fusion: score = sum over lists of 1 / (k + rank)."""
    scores, hits = {}, {}
    for hits_list in lists:
        for rank, h in enumerate(hits_list, 1):
            scores[h["id"]] = scores.get(h["id"], 0.0) + 1 / (k + rank)
            hits.setdefault(h["id"], h)
    return [{**hits[i], "score": s} for i, s in sorted(scores.items(), key=lambda x: -x[1])]


def rerank(q: str, hits: list[dict], top: int = 5) -> list[dict]:
    scores = _reranker().predict([(q, h["text"]) for h in hits])
    ranked = sorted(zip(hits, scores), key=lambda x: -x[1])[:top]
    return [{**h, "score": float(s)} for h, s in ranked]


def search(q: str, mode: str | None = None) -> list[dict]:
    mode, top, n = mode or CFG["retrieval"], CFG["top_k"], CFG["candidates"]
    if mode == "vector":
        return vector(q, top)
    fused = rrf([bm25(q, n), vector(q, n)])
    return fused[:top] if mode == "hybrid" else rerank(q, fused, top)


def cite(h: dict) -> str:
    return f"[{h['doc']} §{h['section']} p.{h['page']}]"


if __name__ == "__main__":
    q, modes = sys.argv[1], sys.argv[2:] or [CFG["retrieval"]]
    for mode in modes:
        print(f"\n== {mode}")
        for h in search(q, mode):
            print(f"{h['score']:.4f} {cite(h)}")
