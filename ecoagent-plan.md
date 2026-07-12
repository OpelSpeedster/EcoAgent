# EcoAgent v2 — Complete Rebuild Plan

## Top-Level Overview

**Goal:** Rebuild EcoAgent from scratch as a full-featured Gradio web application using `ibm-watsonx-ai` SDK directly (ModelInference.chat() with `ibm/granite-3-3-8b-instruct`). The IBM Orchestrate REST API integration is abandoned — it was not reachable via a public REST endpoint. The IBM Cloud API key (`CLOUD_API` from `.env.example`) works for direct watsonx.ai SDK calls.

**What gets replaced/deleted:**
- `rag_pipeline.py` → replaced by `watsonx_client.py`
- `app.py` → fully rewritten
- `ibm-credentials.env` → replaced by `.env` (simpler var names)
- `requirements.txt` → updated
- `ecoagent-plan.md` → this file supersedes it

**Architecture:**
```
.env
  └─ WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL
        │
        ▼
watsonx_client.py          ← ModelInference wrapper, AGENT_INSTRUCTIONS, impact lookup table
        │
        ▼
app.py                     ← Gradio Blocks UI: Chat + Dashboard + Recycling + Profile
        │
        ├─ gr.Blocks (custom CSS/JS, Bootstrap CDN, dark mode)
        ├─ Chat tab          ← primary interaction, eco score streak
        ├─ Dashboard tab     ← CO₂/water/waste savings visualised
        ├─ Recycling tab     ← material lookup → guidelines + product recommendations
        └─ Profile tab       ← household members, habits, location (India-specific)
```

**IBM SDK usage (confirmed working):**
```python
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
model = ModelInference(model_id="ibm/granite-3-3-8b-instruct", credentials=..., project_id=...)
response = model.chat(messages=[{"role":"system","content":"..."}, {"role":"user","content":"..."}])
answer = response["choices"][0]["message"]["content"]
```

**Non-Goals:**
- No Exa MCP / web search (user dropped that requirement in the new prompt)
- No IBM Orchestrate REST API
- No FAISS / local embeddings

---

## Environment Variables (new `.env`)

| Variable | Value | Purpose |
|---|---|---|
| `WATSONX_API_KEY` | `CLOUD_API` value from `.env.example` | IBM Cloud API key for watsonx.ai |
| `WATSONX_PROJECT_ID` | User must fill in from watsonx.ai Studio | Required by ModelInference |
| `WATSONX_URL` | `https://eu-de.ml.cloud.ibm.com` | watsonx.ai eu-de (Frankfurt) endpoint |

**Region confirmed:** `eu-de` (Frankfurt) — platform at `https://eu-de.dataplatform.cloud.ibm.com`
**`ibm-credentials.env`**: Delete — fully superseded by `.env`.

---

## Sub-Tasks

---

### Sub-Task 1: Create `.env` and update `ibm-credentials.env`

**Intent:** Replace the sprawling `ibm-credentials.env` with a clean `.env` using the new variable names. Keep `ibm-credentials.env` as a legacy backup comment only.

**Expected Outcomes:**
- `.env` exists with `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL`
- `.env.example` updated to document the new vars (without real values for PROJECT_ID)
- `ibm-credentials.env` cleared out or noted as superseded

**Todo List:**
1. Write `.env` with `CLOUD_API` value mapped to `WATSONX_API_KEY`
2. Set `WATSONX_URL=https://us-south.ml.cloud.ibm.com`
3. Leave `WATSONX_PROJECT_ID=` blank (user must fill in from watsonx.ai Studio)
4. Update `.env.example` to document all three vars without values

**Status:** `[ ] pending`

---

### Sub-Task 2: Create `watsonx_client.py`

**Intent:** All IBM watsonx.ai SDK logic in one file: `AGENT_INSTRUCTIONS` block, carbon impact lookup table, and `get_eco_answer(messages, profile)` function.

**Expected Outcomes:**
- `watsonx_client.py` is importable and `get_eco_answer()` returns a string
- `AGENT_INSTRUCTIONS` is a clearly labelled, easily editable multi-line string at the top
- Carbon/resource impact lookup table covers ≥15 common actions with CO₂/water/waste values
- If SDK call fails, raises `RuntimeError` with a descriptive message
- `project_id` must be set; if missing raises a clear error at import time

**Todo List:**
1. `load_dotenv(".env")` at module top
2. Write `AGENT_INSTRUCTIONS` constant — covers:
   - Persona/tone: friendly, concise, India-aware eco advisor
   - Answer structure: quick tip → why it matters (1 line) → optional resource
   - Safety rules: no invented stats, label estimates vs lookup values
   - Sustainability focus areas: plastic, energy, water, travel, food, waste
   - India-specific context: regional schemes (PM Surya Ghar, Swachh Bharat, FAME), local recycling norms, common household practices
3. Write `IMPACT_TABLE: dict[str, dict]` — keyed by action slug, values: `{co2_kg_year, water_L_day, waste_kg_year, label}`; cover actions like: cloth bags, LED bulbs, solar panels, composting, public transport, short showers, rainwater harvesting, etc.
4. Write `_build_system_prompt(profile: dict) -> str` — injects profile (location, members, habits) into the system message alongside `AGENT_INSTRUCTIONS`
5. Write `get_eco_answer(messages: list[dict], profile: dict) -> str`:
   - Builds `[system_msg] + messages` list
   - Calls `ModelInference.chat()` with `max_tokens=800, temperature=0.7`
   - Returns `response["choices"][0]["message"]["content"]`
6. Write `get_recycling_guide(material: str, location: str) -> str` — a focused single-turn call to Granite to return recycling instructions for a material in an Indian city context
7. Startup validation: raise `EnvironmentError` if `WATSONX_API_KEY` or `WATSONX_URL` is missing

**Relevant Context:**
- SDK: `ibm_watsonx_ai==1.5.14`
- `Credentials(url=WATSONX_URL, api_key=WATSONX_API_KEY)`
- `ModelInference(model_id="ibm/granite-3-3-8b-instruct", credentials=creds, project_id=WATSONX_PROJECT_ID)`
- Chat response: `response["choices"][0]["message"]["content"]`
- `WATSONX_PROJECT_ID` may be empty during dev — handle gracefully

**Status:** `[ ] pending`

---

### Sub-Task 3: Create `app.py` — Gradio Blocks UI

**Intent:** Full Gradio Blocks application with 4 tabs, Bootstrap styling, dark mode, and session state.

**Expected Outcomes:**
- `python app.py` launches on `http://localhost:7860`
- Chat tab works end-to-end with Granite via `watsonx_client.get_eco_answer()`
- Dashboard tab shows live session-based eco score + cumulative CO₂/water/waste savings
- Recycling tab has a material input + location dropdown + Granite-powered guide output
- Profile tab captures household members, location (Indian cities), habits
- Dark mode toggle works
- Mobile-responsive via Bootstrap grid
- All state is session-based (gr.State)

**Todo List:**

**3a. Custom CSS/JS:**
1. Define `CUSTOM_CSS` string: Bootstrap 5 CDN via `gr.HTML`, eco green palette (`#2d6a4f`, `#52b788`), card shadows, chat bubble styles, animated eco score ring, dark mode variables
2. Define eco score calculation: `score = min(100, len(logged_actions) * 10)` per session

**3b. Chat Tab:**
1. `gr.Chatbot` with custom avatar (leaf emoji) and markdown rendering
2. Message input + Send button
3. Under the chat: "🌱 Log this action" button → increments session action counter → updates eco score
4. Eco score display: circular progress indicator (CSS-only, value from gr.State)
5. Weekly streak counter (session days active — session-based approximation)
6. `chat_submit(message, history, profile_state, actions_state)` → calls `get_eco_answer()` → returns updated history + updated state

**3c. Dashboard Tab:**
1. Header: "Your Eco Impact This Session"
2. Three metric cards: CO₂ saved (kg), Water saved (L), Waste diverted (kg) — computed from logged actions via `IMPACT_TABLE`
3. Eco score gauge (HTML/CSS ring)
4. Household summary: member count, location
5. `update_dashboard(actions_state, profile_state)` → returns HTML string of metric cards

**3d. Recycling Guide Tab:**
1. Material dropdown: Paper, Plastic, Glass, E-waste, Metal, Organic, Batteries, Clothing
2. City dropdown: 15 major Indian cities
3. "Get Guide" button → calls `get_recycling_guide()` → renders in `gr.Markdown`
4. Below: eco-friendly product recommendation section (hardcoded lookup per material category)

**3e. Profile Tab:**
1. Household name input
2. Location dropdown (Indian states + major cities)
3. Member count slider (1–10)
4. Habits checklist: vegetarian diet, uses public transport, has solar panels, composts, uses cloth bags, avoids single-use plastic, harvests rainwater
5. "Save Profile" button → updates `profile_state`
6. Profile summary card shown after save

**3f. App assembly:**
1. `gr.Blocks(theme=gr.themes.Soft(primary_hue="green"), css=CUSTOM_CSS)` with `gr.HTML` Bootstrap CDN inject
2. Dark mode toggle button at top right using `gr.HTML` + JS `localStorage`
3. All tabs inside `gr.Tabs`
4. `demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))`
5. `if __name__ == "__main__":` guard

**Status:** `[ ] pending`

---

### Sub-Task 4: Update `requirements.txt`

**Intent:** Minimal, pinned dependency list for the new architecture.

**Expected Outcomes:**
- Only packages actually used are listed
- Installs cleanly on Python 3.10+ in a fresh HF Spaces environment

**Todo List:**
1. Keep: `gradio`, `ibm-watsonx-ai`, `python-dotenv`, `requests`
2. Remove: `langchain`, `langchain-community`, `faiss-cpu`, `sentence-transformers` (not used)
3. Pin versions based on what is installed in `.venv`

**Status:** `[ ] pending`

---

### Sub-Task 5: Update `README.md` and `AGENTS.md`

**Intent:** Update docs to reflect the new architecture. HF Spaces front-matter, new env var names, deployment steps.

**Todo List:**
1. Update `README.md` HF Spaces YAML: keep gradio SDK, update description
2. Document the 3 new env vars (`WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL`)
3. Add "How to get a `WATSONX_PROJECT_ID`" section (watsonx.ai Studio → create project → copy ID)
4. Update `AGENTS.md` to note `rag_pipeline.py` is deleted, new entry point is `watsonx_client.py`

**Status:** `[ ] pending`

---

## Implementation Order

```
Sub-Task 1 (.env)
      ↓
Sub-Task 2 (watsonx_client.py)   ← core logic, must exist before app.py imports it
      ↓
Sub-Task 3 (app.py)              ← largest file, depends on watsonx_client
      ↓
Sub-Task 4 (requirements.txt)    ← parallel with Sub-Task 3
      ↓
Sub-Task 5 (README + AGENTS.md)  ← final docs
```

---

## Files to Delete After Implementation

- `rag_pipeline.py` — replaced by `watsonx_client.py`
- `embed.txt` — was a debugging artifact, no longer needed
- `ibm-credentials.env` — replaced by `.env`
- `__pycache__/` — stale cache from old modules

---

## Open Questions / Notes

1. **`WATSONX_PROJECT_ID`** is required by the SDK for `ModelInference`. The user must create a project in watsonx.ai Studio (https://us-south.dataplatform.cloud.ibm.com/) and copy the project ID. The app should show a clear setup error if it is missing.
2. **`ibm/granite-3-3-8b-instruct`** is the latest model in the installed SDK. If the user's watsonx.ai project doesn't have access to it, fallback to `ibm/granite-13b-chat-v2`.
3. **Session state**: All eco score and action logging is in-memory `gr.State` — no database. This resets on page refresh, which is acceptable per the spec ("session-based is fine").
4. **Impact numbers in `IMPACT_TABLE`**: Sourced from well-known lifecycle assessment references (IPCC, EPA, Indian BEE data). Each entry will note its source category (lookup vs estimate).
