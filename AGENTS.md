# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project

EcoAgent v2 — A Gradio Blocks web app for eco lifestyle advice, powered by **IBM Granite** (`ibm/granite-3-3-8b-instruct`) via the `ibm-watsonx-ai` SDK. India-focused with 4 tabs: Chat, Dashboard, Recycling Guide, Household Profile.

**IBM Orchestrate REST API is NOT used** — direct SDK calls to watsonx.ai only.

## Stack

- **Runtime:** Python 3.14 via `uv` (venv at `.venv/`)
- **Package manager:** `uv` — always use `uv pip install` / `uv run python`, NOT bare `pip` or `python`
- **System Python is 3.11 (Miniconda)** — unrelated to this project's venv
- **Target deploy:** Hugging Face Spaces (Gradio SDK)

## Key Commands

```bash
uv pip install -r requirements.txt   # install deps
uv run python app.py                  # run locally → http://localhost:7860
```

## Critical Gotchas

- **`.env` is gitignored** — cannot be written by file tools. Use `Set-Content` PowerShell command instead.
- **`WATSONX_PROJECT_ID` is mandatory** — the SDK raises an error without it. Get it from: `https://eu-de.dataplatform.cloud.ibm.com` → project → Manage → General → Project ID.
- **Region is eu-de (Frankfurt)** — `WATSONX_URL=https://eu-de.ml.cloud.ibm.com`. Do not use `us-south`.
- **Model lazy-init** — `_get_model()` in `watsonx_client.py` initialises `ModelInference` on the first call, not at import. Import-time errors = missing env vars. First-call errors = bad project ID or model access.
- **`load_dotenv(".env")` explicit path** — both `app.py` and `watsonx_client.py` call this. The default `load_dotenv()` looks for `.env` by name; the explicit path ensures it works regardless of CWD.
- **Chat history format** — Gradio passes history as `list[list[str, str]]` (pairs). `chat_submit()` unpacks this manually into `{"role":..., "content":...}` dicts before calling `get_eco_answer()`.
- **`dashboard_html` is defined inside the Tab 2 block** — it's referenced by `save_profile()` in Tab 4. Both must be inside the same `gr.Blocks` context.

## Architecture

```
.env
 └─ WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL
        │
        ▼
watsonx_client.py
  ├─ AGENT_INSTRUCTIONS  ← edit to customise persona/tone/focus
  ├─ IMPACT_TABLE        ← 20 actions with CO2/water/waste lookup values
  ├─ PRODUCT_RECS        ← static eco-product recs per material category
  ├─ get_eco_answer()    ← multi-turn chat, builds [system]+messages list
  ├─ get_recycling_guide() ← single-turn recycling lookup call
  └─ compute_session_impact() ← aggregates logged actions → metric dict
        │
        ▼
app.py (Gradio Blocks)
  ├─ Tab 1: Chat          ← chatbot + action chip logger + eco score ring
  ├─ Tab 2: Dashboard     ← HTML metric cards from compute_session_impact()
  ├─ Tab 3: Recycling     ← material+city dropdowns → get_recycling_guide()
  └─ Tab 4: Profile       ← household form → profile_state (gr.State)
```

## Environment Variables

| Variable | Source | Purpose |
|---|---|---|
| `WATSONX_API_KEY` | `CLOUD_API` in `.env.example` | IBM Cloud API key |
| `WATSONX_PROJECT_ID` | watsonx.ai Studio | SDK project scope — required |
| `WATSONX_URL` | `https://eu-de.ml.cloud.ibm.com` | eu-de watsonx.ai endpoint |

## Deleted Files (v1 → v2)

- `rag_pipeline.py` → replaced by `watsonx_client.py`
- `ibm-credentials.env` → replaced by `.env`
- `embed.txt` → was a debugging artifact; deleted
