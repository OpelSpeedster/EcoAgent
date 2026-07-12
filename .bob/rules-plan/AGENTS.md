# AGENTS.md — Plan Mode

This file provides guidance to agents planning work in this repository.

## Non-Obvious Architectural Constraints

- **Orchestrate endpoint path is unverified** — `ecoagent-plan.md` assumes `/v1/chat` or `/v1/chat/completions`. The actual IBM watsonx Orchestrate REST path for the au-syd region must be confirmed against IBM docs before finalising `rag_pipeline.py`. Only `rag_pipeline.py` needs changing if the path is wrong.
- **Source citations are best-effort** — Orchestrate may not return `references`/`citations` fields. Any plan that depends on structured source metadata must account for the `[]` fallback path.
- **HF Spaces CPU constraint** — the free tier has no GPU. Any plan that includes `faiss-gpu`, `torch` with CUDA, or `sentence-transformers` with GPU inference will break on deployment.
- **Token caching is a hidden correctness requirement** — any refactor of `rag_pipeline.py` that removes module-level token caching will introduce per-request IAM latency and potential throttling. This is not obvious from the function signature alone.
- **`ecoagent-plan.md` tracks sub-task status** — update `[ ] pending` → `[x] done` in that file as each sub-task completes. It is the single source of truth for implementation progress.
- **No test infrastructure exists** — any plan to add tests must also set up pytest and a test entry point from scratch. There is no existing `conftest.py`, `tests/` directory, or pytest config.
