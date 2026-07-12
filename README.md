# 🌱 EcoAgent — AI-Powered Eco Lifestyle Assistant

An India-focused sustainable living assistant powered by **IBM Granite** via **watsonx.ai**. Chat about eco habits, explore a household impact dashboard, look up local recycling guides, and build a family sustainability profile.

---

## Features

| Tab | What it does |
|---|---|
| 💬 **Chat** | Multi-turn conversation with IBM Granite — personalised eco tips, government schemes, impact estimates |
| 📊 **Dashboard** | Session-based eco score (0–100), CO₂/water/waste savings tracker, household summary |
| ♻️ **Recycling Guide** | City-specific recycling instructions for 8 material categories + eco-friendly product alternatives |
| 🏡 **Profile** | Household members, Indian city, current eco habits — personalises all chat responses |

---

## 💪 Effort Behind This Project

This project is the result of a full **v2 rebuild** with focused work across product design, AI integration and UX:

- Replaced the older pipeline with a new `watsonx_client.py` architecture using IBM Granite + watsonx.ai SDK.
- Designed and built a complete 4-tab Gradio application (`Chat`, `Dashboard`, `Recycling Guide`, `Profile`).
- Created impact tracking logic (eco score + CO₂/water/waste calculations) with session-aware state handling.
- Added India-focused sustainability guidance, recycling flows, and household personalization.
- Reworked environment setup, dependency management, and deployment readiness for Hugging Face Spaces.

In short: this is not a template drop-in — it reflects significant end-to-end implementation effort from planning to delivery.

---

## Architecture

```
.env  (WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL)
        │
        ▼
watsonx_client.py   ← IBM Granite ModelInference, AGENT_INSTRUCTIONS, IMPACT_TABLE
        │
        ▼
      app.py        ← Gradio Blocks (4 tabs, Bootstrap CSS, dark mode, session state)
```

**Model:** `ibm/granite-4-h-small` (eu-de region, watsonx.ai)  
**Auth:** IBM Cloud API key → watsonx.ai SDK (no Orchestrate REST API)

---

## Environment Variables

Set these as **Secrets** in your Hugging Face Space (Settings → Variables and Secrets)  
or in a local `.env` file (never commit with real values).

| Variable | Required | Description |
|---|---|---|
| `WATSONX_API_KEY` | ✅ | IBM Cloud API key — [get one here](https://cloud.ibm.com/iam/apikeys) |
| `WATSONX_PROJECT_ID` | ✅ | watsonx.ai Studio Project ID (UUID) — see below |
| `WATSONX_URL` | ✅ | watsonx.ai endpoint for your region — default `https://eu-de.ml.cloud.ibm.com` |

### How to get `WATSONX_PROJECT_ID`

1. Go to [https://eu-de.dataplatform.cloud.ibm.com](https://eu-de.dataplatform.cloud.ibm.com)
2. Create or open a project
3. Click the **Manage** tab → **General** section
4. Copy the **Project ID** (a UUID like `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
5. Add it to `.env` as `WATSONX_PROJECT_ID=<your-uuid>`

### Regional watsonx.ai URLs

| Region | URL |
|---|---|
| EU Frankfurt (default) | `https://eu-de.ml.cloud.ibm.com` |
| US Dallas | `https://us-south.ml.cloud.ibm.com` |
| UK London | `https://eu-gb.ml.cloud.ibm.com` |
| Japan Tokyo | `https://jp-tok.ml.cloud.ibm.com` |
| Australia Sydney | `https://au-syd.ml.cloud.ibm.com` |

---

## Local Development

### Prerequisites
- Python 3.10+ (Python 3.14 via `uv` is configured in `.venv`)
- [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`

### Steps

```bash
# 1. Clone the repo
git clone https://huggingface.co/spaces/<your-username>/ecoagent
cd ecoagent

# 2. Install dependencies
uv pip install -r requirements.txt
# or: pip install -r requirements.txt

# 3. Configure credentials
# Copy .env.example to .env and fill in your values:
cp .env.example .env
# Edit .env — set WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL

# 4. Run
uv run python app.py
# → Open http://localhost:7860
```

---

## Customising the Agent

Open [`watsonx_client.py`](watsonx_client.py) and edit the `AGENT_INSTRUCTIONS` constant at the top of the file. You can change:

- **Persona & tone** — make it more formal, more playful, multilingual, etc.
- **Focus areas** — add specific sustainability topics (e.g. marine conservation)
- **India-specific context** — add regional schemes, local brands, city-specific advice
- **Safety rules** — tighten or relax what the agent will/won't say
- **Answer structure** — change the tip → why → impact → resource format

The `IMPACT_TABLE` dict below it controls the carbon/water/waste numbers shown in the Dashboard tab — add new actions or update existing values there.

---

## Project Files

| File | Purpose |
|---|---|
| `app.py` | Gradio Blocks UI — all 4 tabs, callbacks, CSS |
| `watsonx_client.py` | IBM watsonx.ai SDK wrapper, agent instructions, impact table |
| `requirements.txt` | Pinned Python dependencies |
| `.env` | Local credentials (never commit) |
| `.env.example` | Template — safe to commit |
| `ecoagent-plan.md` | Implementation plan and architecture decisions |

---

## Disclaimer

Answers are AI-generated by IBM Granite. Impact figures labelled `[Lookup]` are sourced from IPCC AR6, BEE India, and CPCB data. Figures labelled `[Estimate]` are model-generated approximations. Always verify government schemes and legal/financial details with official sources.
