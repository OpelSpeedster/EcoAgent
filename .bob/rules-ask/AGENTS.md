# AGENTS.md — Ask Mode

This file provides guidance to agents answering questions about this repository.

## Non-Obvious Context

- **The `.venv` does NOT contain the project's actual runtime dependencies.** It only has Flask/Werkzeug from prior scaffolding. The app cannot run until `uv pip install -r requirements.txt` is executed.
- **`ibm-credentials.env` is NOT gitignored** — it contains real API keys and is committed to the repo. When answering questions about secrets management, note this is intentional for HF Spaces deployment (where secrets are injected as env vars at runtime, but the file exists locally for dev).
- **"RAG pipeline" is a misnomer** — there is no local retrieval. `rag_pipeline.py` is purely an IBM Orchestrate REST API client. Retrieval and generation both happen inside Orchestrate server-side.
- **The plan file `ecoagent-plan.md`** is the authoritative source of architectural decisions (Orchestrate REST vs local FAISS, auth flow, etc.). Refer to it when explaining design choices.
- **Python version split:** system Python = 3.11 (Miniconda), project Python = 3.14 (uv-managed). Questions about compatibility or imports must account for this.
