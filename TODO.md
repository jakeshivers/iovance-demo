# Progress — Regulatory RAG Demo

Last updated: 2026-10-02 · Repo: https://github.com/jakeshivers/iovance-demo (public, `main` in sync)

## Done: all phases 1–9 committed and pushed
| Phase | Commit | What |
|---|---|---|
| 1 Infra | — | OpenSearch 2.17 in Docker, `regdocs` index (BM25 `text`, 384-d HNSW `embedding`, doc/section/page) |
| 2 Ingest | d397833 | pypdf, heading chunking (~500 tok / 50 overlap), bge-small embeddings, bulk index |
| 3 Retrieve | f7be0f9 | bm25, vector, hand-written RRF (k=60), bge-reranker; mode in `config.yaml` |
| 4 Generate | 1a3ddc3 | `LLM` interface (Ollama + Anthropic), `[doc §section p.page]` citations, refuse if top rerank < 0.3 |
| 5 Guard | ef961eb | Presidio PII redaction (logged to `rag.log`), `<document>` data wrapping, `docs/zz_poisoned_test.pdf` (CANARY-7731) |
| 6 Eval | 5fe4462 | 30-Q golden set, `eval/run_eval.py`, GitHub Action recall gate (baseline 0.96) |
| 7 MCP + README | e22f37c | FastMCP `search_regulatory_docs` (`mcp<2` pinned — 2.x renamed FastMCP), README w/ mermaid, eval table, AWS section |
| 8 UI | aa48700 | Streamlit `app.py`: question box, mode dropdown, cited answer, source cards, refusal box |
| 9 Agent | 70ac72d | `rag/agent.py` compliance gap assessor: raw Anthropic tool-use loop, `report_findings`, ⚠ UNVERIFIED citation guardrail, max 10 turns |

### Post-phase additions (all pushed)
- 6ceb649 — CLAUDE.md: removed "UI" from Out of Scope (contradicted Phase 8).
- a68f8ca — UI document library sidebar: `static` → `docs/` symlink + `.streamlit/config.toml` static serving.
- 2851fb4 — Source card page numbers link to `…pdf#page=N`.
- 38a05c5 — README: agent section (diagram, example table), commands table, agent row in AWS table.
- f9e1c81 — README: "Swap to AWS (design note)" — demo is fully local, nothing on AWS is implemented.
- 6445f09 — UI: "Gap assessment (agent)" tab; Ask answers cached (`st.cache_data`) so reruns don't re-query.
- 5c84164 — TODO rewritten with phases 6–9, UI additions, CI and eval results.
- 77ac10f / 5639445 — Repo-facing docs made neutral: TODO trimmed to project status; README + CLAUDE.md
  goal line now "Demo, not a product."; private notes ignored locally via `.git/info/exclude` (not `.gitignore`).
  Git history intentionally not rewritten — older commits keep the earlier wording.

## Eval results (local, CPU only)
| mode | llm | recall@5 | citation acc | refusal acc | p50 latency |
|---|---|---|---|---|---|
| vector | anthropic | 96% | 84% | 90% | 4.59s |
| hybrid | anthropic | 100% | 88% | 93% | 5.08s |
| hybrid_rerank | anthropic | 100% | 88% | 93% | 23.04s |
| vector | ollama | 96% | 72% | 90% | 51.66s |
| hybrid | ollama | 100% | 72% | 93% | 59.11s |
| hybrid_rerank | ollama | 100% | 72% | 93% | 71.55s |

- CI (GitHub, retrieval-only): **passed**, hybrid_rerank recall@5 = 1.000 vs 0.96. Vector scored 92% in CI vs 96%
  locally (fresh index on different hardware; near-tie ranking — unconfirmed). Gate only checks hybrid_rerank.
- Agent on LIMS scenario: flags shared login + disabled audit trails as high-severity cited gaps, ~25–65s;
  retrieves the poisoned doc and ignores it.

## Environment notes
- Ollama installed user-local (no sudo): `~/.local/ollama/bin/ollama serve`. Not on PATH; restart after reboot.
- `ANTHROPIC_API_KEY` lives in `~/.zshrc`; Claude Code sessions only see it via `zsh -ic '...'`.
- Run UI: `uv run streamlit run app.py` (from zsh). Restart Streamlit after config changes.
- `eval/run_eval.py` removes `zz_poisoned_test` from the index; `uv run python -m rag.ingest` restores it.

## Open items
- Phase 7 acceptance: MCP tool not yet tested from Claude Desktop (not installed here; stdio smoke test passes).
- Optional: agent eval scenarios (expected gaps per scenario) in the golden set.

## Known limitations
- 2 wrongful refusals (shared-login, blank-forms Qs): right chunk #1 but rerank < 0.3. Threshold deliberately
  not tuned (tattoo-ink refusal Q scores 0.061).
- Heading parser misses data-integrity Q13; AI doc `i.` items labeled `IV.A.4.i`.
- Reranking 40 candidates on CPU ~10s per query.
- Anthropic SDK 1.11 rejects `temperature`; Claude calls use default sampling.
