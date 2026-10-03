"""Read-only MCP server exposing hybrid+rerank search over FDA guidance."""
from mcp.server.fastmcp import FastMCP

from rag.guard import redact, wrap
from rag.retrieve import cite, search

mcp = FastMCP("regulatory-docs")


@mcp.tool()
def search_regulatory_docs(query: str) -> str:
    """Search FDA regulatory guidance; returns top chunks, each tagged with a [doc §section p.page] citation."""
    hits = search(redact(query))
    return "\n\n".join(f"score={h['score']:.3f}\n{wrap(cite(h), h['text'])}" for h in hits)


if __name__ == "__main__":
    mcp.run()
