# AGENTS.md — Agent (Coding) Mode

This file provides guidance to agents when writing or modifying code in this repository.

## Non-Obvious Coding Rules

- **Use `uv run python` / `uv pip`** — the project venv is managed by `uv` (Python 3.14). Bare `python` resolves to system Miniconda 3.11 and will NOT see project packages.
- **`load_dotenv("ibm-credentials.env")` — explicit path required.** `python-dotenv`'s default `load_dotenv()` looks for `.env`. This project's IBM credentials are in `ibm-credentials.env`. Without the explicit filename, all `ORCHESTRATE_*` vars will be `None` at runtime.
- **IAM token must be cached at module level** — store token + expiry in `rag_pipeline.py` module globals (`_cached_token`, `_token_expiry`). A new IAM HTTP call on every `get_answer()` call will cause ~300ms latency per message and risks IAM rate limiting.
- **`get_answer` signature is a hard contract** — `app.py` pattern-matches on `tuple[str, list[str]]`. Changing the return type (e.g., returning a dict) will silently break source citation rendering in the UI.
- **`gr.ChatInterface` wrapping pattern** — to add a footer, `ChatInterface` must be instantiated *inside* a `gr.Blocks()` context. Instantiating it outside and then wrapping breaks the layout.
- **No Flask in this project** — `.venv` has Flask installed from prior work but it is not used. Do not import or reference it.
- **`requirements.txt` must NOT pin `faiss-cpu` to a GPU variant** — HF Spaces CPU-tier will fail if `faiss-gpu` is specified.
