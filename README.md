
# 🌱 EcoAgent — AI-Powered Eco Lifestyle Assistant

An India-focused sustainable living assistant powered by **IBM Granite** via **watsonx.ai**. Chat about eco habits, explore a household impact dashboard, look up local recycling guides, and build a family sustainability profile. 

## This is the latest update of the project with Agentic AI: (https://github.com/OpelSpeedster/EcoAgent-AAI-) 

**Classification:** Agentic AI Application with Prompt Engineering

---

## Features

| Tab | What it does |
|---|---|
| 💬 **Chat** | Multi-turn conversation with IBM Granite — personalised eco tips, government schemes, impact estimates. **Agent Mode** enables multi-step reasoning with 5 tools. |
| 📊 **Dashboard** | Session-based eco score (0–100), CO₂/water/waste savings tracker, household summary |
| ♻️ **Recycling Guide** | City-specific recycling instructions for 8 material categories + eco-friendly product alternatives |
| 🏡 **Profile** | Household members, Indian city, current eco habits — personalises all chat responses |

---

## Agent Mode

EcoAgent features an **agentic AI loop** that can use tools to provide accurate, data-driven answers:

| Tool | Purpose |
|------|---------|
| 🧮 **Impact Calculator** | Get exact CO₂/water/waste numbers for eco actions |
| ♻️ **Recycling Guide** | City-specific recycling instructions |
| 🔍 **Web Search** | Search latest news, schemes, local services |
| 🏛️ **Scheme Checker** | Indian government scheme details and eligibility |
| 👥 **Household Profiler** | Personalized action plan based on profile |

**How it works:**
1. Enable "Agent Mode" checkbox in Chat tab
2. Ask a question
3. Agent reasons step-by-step, calls tools as needed
4. See which tools were used below the response

**Date Accuracy Fix:**
- System prompt includes `TODAY'S DATE` so the LLM knows the current date
- Web search results include `Search conducted on: <date>` header
- LLM is instructed to trust search results over its training data
- Prevents hallucinated outdated dates like "August 2025"

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
tools.py            ← 5 tool definitions, executor, scheme database
        │
        ▼
agent.py            ← Agentic loop with multi-step reasoning
        │
        ▼
app.py              ← Gradio Blocks (4 tabs, ultra-light eco green theme, session state)

```

**Model:** `ibm/granite-4-h-small` (eu-de region, watsonx.ai)  
**Auth:** IBM Cloud API key → watsonx.ai SDK (no Orchestrate REST API)

---

## How It Works

EcoAgent uses **prompt engineering** + **agentic AI** to transform IBM Granite into a domain-specific eco advisor:

1. **System Prompt:** 86-line `AGENT_INSTRUCTIONS` defining persona, output format, focus areas, and guardrails
2. **Static Knowledge:** `IMPACT_TABLE` (20 eco actions) and `PRODUCT_RECS` (8 material categories) injected via prompt
3. **Dynamic Context:** Household profile (members, location, habits) injected per session
4. **Agent Loop:** Multi-step reasoning with tool calls (max 5 iterations)
5. **Tool Execution:** Real-time tool calls with result feedback
6. **Date Injection:** Current date injected into system prompt and search results for accuracy
7. **Output Format:** Fixed 4-part structure (Quick Tip → Why it Matters → Impact → Optional Resource)
8. **Guardrails:** Never invent stats, label [Lookup] vs [Estimate], no medical/financial advice

---

## UI Theme

Ultra-light eco green theme with near-white background and green accents:

- Background: `#fcfcfd` (near white)
- Primary accent: `#2e7d50` (green)
- Cards: `#ffffff` with subtle shadows
- Text: `#1c1c1e` (near black), muted: `#4a4a4e`
- Borders: `#e4e4e7` (light gray)
- CheckboxGroup styled as selectable pills/chips

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
| `app.py` | Gradio Blocks UI — 4 tabs, callbacks, CSS theme |
| `watsonx_client.py` | IBM watsonx.ai SDK wrapper, agent config, impact data |
| `tools.py` | Agent tool definitions, executor, scheme database |
| `agent.py` | Agentic loop with multi-step reasoning |
| `requirements.txt` | Pinned Python dependencies (5 packages) |
| `.env` | Local credentials (gitignored) |
| `.env.example` | Template — safe to commit |
| `ecoagent-plan.md` | Implementation plan and architecture decisions |
| `architecture.png` | Architecture blueprint diagram |
| `fill.txt` | PPT content fill for presentation |

---

## Disclaimer

Answers are AI-generated by IBM Granite. Impact figures labelled `[Lookup]` are sourced from IPCC AR6, BEE India, and CPCB data. Figures labelled `[Estimate]` are model-generated approximations. Always verify government schemes and legal/financial details with official sources.
