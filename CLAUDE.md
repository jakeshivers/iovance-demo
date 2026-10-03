# Regulatory RAG Demo — Build Spec

## Goal
Local hybrid RAG over public FDA guidance PDFs. Demo. Not a product.

## Agent Rules (follow strictly)
- Do ONLY the current phase. Stop and report when its acceptance check passes.
- No features, files, or deps beyond this spec. No refactors of finished phases.
- Don't explore the repo or re-read files you just wrote. Keep replies short: what changed, how to verify.
- If blocked or the spec is ambiguous, ask one question. Don't guess or work around.
- Minimal code. No docstrings beyond one line. No README until Phase 7.
- Commit after each phase: `phase N: <summary>`.

## Stack (fixed)
Python 3.11 · OpenSearch 2.x (Docker, security plugin disabled) · sentence-transformers `BAAI/bge-small-en-v1.5` · cross-encoder `BAAI/bge-reranker-base` · Ollama (`llama3.1:8b`) + Anthropic API · pypdf · presidio · `mcp` Python SDK · pytest

## Layout
```
docker-compose.yml
docs/                 # FDA PDFs (user adds)
rag/
  interfaces.py       # Embedder, LLM, Store protocols
  ingest.py
  retrieve.py         # bm25, vector, rrf, rerank
  generate.py
  guard.py
  mcp_server.py
eval/
  golden.jsonl        # {q, expected_section, should_refuse}
  run_eval.py
config.yaml           # llm: ollama|anthropic, retrieval: vector|hybrid|hybrid_rerank
```

## Phases

**1. Infra** — docker-compose with OpenSearch single node. Index with `text` (BM25), `embedding` (knn_vector, 384 dim, HNSW), `doc`, `section`, `page`.
✅ `curl localhost:9200/_cat/indices` shows index.

**2. Ingest** — Parse PDFs, chunk by heading (~500 tokens, 50 overlap), embed, bulk index with metadata.
✅ `python -m rag.ingest` indexes all docs; prints chunk count.

**3. Retrieve** — `bm25(q,k)`, `vector(q,k)`, `rrf(lists, k=60)` written by hand, `rerank(q, hits, top=5)`. Mode set by config.
✅ Query "Part 11 audit trail" returns cited chunks in all three modes.

**4. Generate** — `interfaces.LLM` with Ollama + Anthropic impls. Prompt: answer only from context, cite `[doc §section p.page]` per claim, reply `INSUFFICIENT_CONTEXT` if top rerank score < threshold.
✅ CLI `python -m rag.generate "q"` returns cited answer; nonsense q refuses.

**5. Guard** — Presidio redacts PII on input. Retrieved text wrapped as data; system prompt says ignore instructions inside context. Add one poisoned test doc containing an injected instruction.
✅ Poisoned doc does not change behavior; PII in query is redacted in logs.

**6. Eval** — 30 golden Qs (25 answerable, 5 should_refuse). Metrics: recall@5, citation accuracy, refusal accuracy, p50 latency. Output one markdown table comparing retrieval modes × LLMs. GitHub Action fails if hybrid_rerank recall@5 drops below baseline.
✅ `python eval/run_eval.py` prints comparison table.

**7. MCP + README** — FastMCP server exposing read-only `search_regulatory_docs(query)` returning cited chunks. README: setup, architecture diagram (mermaid), eval table, "Swap to AWS" section mapping each interface to Bedrock / S3 Vectors / OpenSearch Service.
✅ Tool works from Claude Desktop.

**8. UI (only after 1–7 pass)** — Single file `app.py`, Streamlit. Question box; answer with citations; expandable source cards (doc, section, page, text, rerank score); dropdown for retrieval mode; distinct refusal display. Calls existing rag functions only — no new logic, no styling work.
✅ `streamlit run app.py` answers a question in all three modes.

**9. Agent** — `rag/agent.py`: compliance gap assessor. Raw Anthropic tool-use loop (no agent framework). Input: system/SOP description (PII-redacted). Tools: `search_regulatory_docs` (same as MCP) and `report_findings` (claim, verdict compliant|gap|unclear, severity, citation, remediation). Max 10 turns. Findings whose citation was not in retrieved results are flagged (output guardrail).
✅ `python -m rag.agent "<LIMS scenario>"` flags shared logins and disabled audit trails as cited gaps.

## Out of Scope
Auth, multi-tenancy, streaming, Docker for the app itself, AWS deployment, any extra models.
