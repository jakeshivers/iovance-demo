# Progress — Regulatory RAG Demo

Last updated: 2026-10-02

## Done (committed)
- Phase 1 — OpenSearch + `regdocs` index (`docker-compose.yml`, init-index container)
- Phase 2 — ingest: heading chunking, bge-small embeddings, bulk index (145 chunks incl. poisoned doc)
- Phase 3 — bm25 / vector / hand-written RRF / bge-reranker; mode in `config.yaml`
- Phase 4 — `LLM` interface (Ollama + Anthropic), cited answers, refusal if top rerank < 0.3
- Phase 5 — Presidio PII redaction (`rag.log`), `<document>` data wrapping, `docs/zz_poisoned_test.pdf`
- FDA PDFs committed (needed by CI)

## Phase 6 — COMMITTED 5fe4462 (anthropic + ollama tables in README)

### (old notes)
Uncommitted: `eval/golden.jsonl`, `eval/run_eval.py`, `.github/workflows/eval.yml`,
`config.yaml` (`baseline_recall_at_5: 0.96`), `rag/interfaces.py` (`max_tokens` 1024 -> 2048).

Verified so far (`--llms none`, retrieval only):

| mode | recall@5 | refusal acc | p50 latency |
|---|---|---|---|
| vector | 96% | 93% | 0.99s |
| hybrid | 100% | 93% | 1.05s |
| hybrid_rerank | 100% | 93% | 10.83s |

- `--check-baseline` exits 0 at 0.96, exits 1 at 1.01 (tested).
- 93% refusal = 2 wrongful refusals (shared-login, blank-forms Qs): right chunk ranked #1 but
  rerank score < 0.3. Deliberately NOT tuned (tattoo-ink refusal Q scores 0.061).

### Next steps
- 2026-10-02: Ollama installed user-local (no sudo) at `~/.local/ollama/bin/ollama`; start with `~/.local/ollama/bin/ollama serve`. API key only visible via `zsh -ic '...'`. Anthropic + Ollama (all 3 modes) evals launched.
1. Ollama: user installs (`curl -fsSL https://ollama.com/install.sh | sh`, needs sudo) and
   runs `ollama pull llama3.1:8b`. No GPU here -> CPU, ~1–2 min/answer.
   Decide: full 3-mode Ollama run (~1.5–3 h, background) or hybrid_rerank only.
2. Confirm Claude Code session can see `ANTHROPIC_API_KEY` (wasn't visible to the old session).
3. Run `uv run python eval/run_eval.py` (default: ollama + anthropic). Paste table into README later.
4. Commit: `phase 6: golden set, eval runner, CI recall gate`.
5. Note: eval removes `zz_poisoned_test` from the index; `uv run python -m rag.ingest` restores it.

## Phase 7 — COMMITTED e22f37c. Stdio smoke test passes; awaiting Claude Desktop check (not installed on this machine).
## Phase 8 — COMMITTED (app.py). AppTest passes all 3 modes + refusal. CLAUDE.md "Out of Scope: UI" fix left to user (edit blocked by auto-mode).

## Known limitations (for interview / README)
- Heading parser misses data-integrity Q13; AI doc `i.` items labeled `IV.A.4.i`.
- Reranking 40 candidates on CPU ~10s per query.
- Anthropic SDK 1.11 rejects `temperature`; Claude calls use default sampling.
