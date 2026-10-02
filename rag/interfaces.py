"""Swappable interfaces and their local implementations."""
from typing import Protocol

from opensearchpy import OpenSearch, helpers
from sentence_transformers import SentenceTransformer

INDEX = "regdocs"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class Embedder(Protocol):
    def embed(self, texts: list[str], query: bool = False) -> list[list[float]]: ...


class Store(Protocol):
    def replace_doc(self, doc: str, chunks: list[dict]) -> int: ...


class BgeEmbedder:
    def __init__(self, model: str = "BAAI/bge-small-en-v1.5"):
        self.model = SentenceTransformer(model)

    def embed(self, texts, query=False):
        if query:
            texts = [QUERY_PREFIX + t for t in texts]
        return self.model.encode(texts, normalize_embeddings=True, batch_size=32).tolist()


class OpenSearchStore:
    def __init__(self, host: str = "http://localhost:9200", index: str = INDEX):
        self.client, self.index = OpenSearch(host), index

    def replace_doc(self, doc, chunks):
        self.client.delete_by_query(index=self.index, body={"query": {"term": {"doc": doc}}}, refresh=True)
        actions = [{"_index": self.index, "_id": f"{doc}-{i}", **c} for i, c in enumerate(chunks)]
        ok, _ = helpers.bulk(self.client, actions, refresh=True)
        return ok
