"""
app.py
------
EcoAgent — Gradio Blocks UI with 4 tabs:
  Chat | Dashboard | Recycling Guide | Household Profile

Features:
  - IBM Granite 4 H Small via watsonx.ai (ibm-watsonx-ai APIClient)
  - Clean light-theme CSS, no dark mode
  - Session-based eco score, action logging, impact dashboard
  - India-specific recycling guide and product recommendations
  - Household/family profile with habit tracking
  - Hugging Face Spaces compatible
"""

import os
import logging

# Fix SSL certificate path for environments where SSL_CERT_FILE points to wrong Python
if "SSL_CERT_FILE" not in os.environ or not os.path.isfile(os.environ.get("SSL_CERT_FILE", "")):
    try:
        import certifi
        os.environ["SSL_CERT_FILE"] = certifi.where()
        os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
    except ImportError:
        pass

import gradio as gr
from dotenv import load_dotenv

from watsonx_client import (
    get_eco_answer,
    get_recycling_guide,
    compute_session_impact,
    IMPACT_TABLE,
    PRODUCT_RECS,
    INDIAN_CITIES,
)
from agent import agent_loop, format_tool_calls

# ---------------------------------------------------------------------------
load_dotenv(".env")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom CSS — light-only eco green theme, polished cards and layout
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --eco-primary:   #2e7d50;
    --eco-secondary: #43a868;
    --eco-light:     #f0f7f3;
    --eco-bg:        #fcfcfd;
    --eco-card:      #ffffff;
    --eco-text:      #1c1c1e;
    --eco-muted:     #6b6b6f;
    --eco-border:    #e4e4e7;
    --eco-shadow:    0 1px 3px rgba(0,0,0,0.04);
    --radius:        6px;
}

body, .gradio-container {
    font-family: 'Inter', system-ui, sans-serif !important;
    background: var(--eco-bg) !important;
    color: var(--eco-text) !important;
}

/* ── Gradio component overrides for ultra-light look ── */
.gradio-container { background: var(--eco-bg) !important; }
.gradio-container .wrap { background: var(--eco-bg) !important; }

/* Tabs */
.tab-nav button {
    font-weight: 500 !important;
    color: var(--eco-muted) !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    background: transparent !important;
    border-radius: 0 !important;
    padding: 8px 16px !important;
}
.tab-nav button.selected {
    color: var(--eco-primary) !important;
    border-bottom: 2.5px solid var(--eco-primary) !important;
    font-weight: 600 !important;
}
.tab-nav button:hover {
    color: var(--eco-primary) !important;
    background: var(--eco-light) !important;
}

/* Buttons */
button.primary, button.primary.lg {
    background: var(--eco-primary) !important;
    border-color: var(--eco-primary) !important;
    color: #fff !important;
    border-radius: var(--radius) !important;
    font-weight: 600 !important;
}
button.primary:hover {
    background: #256a42 !important;
    border-color: #256a42 !important;
}
button.secondary, button.secondary.lg {
    background: var(--eco-light) !important;
    border: 1px solid var(--eco-border) !important;
    color: var(--eco-text) !important;
    border-radius: var(--radius) !important;
    font-weight: 500 !important;
}
button.secondary:hover {
    background: #e4eff0 !important;
    border-color: var(--eco-border) !important;
}

/* Textbox / Dropdown / Slider */
textarea, input[type="text"], .wrap textarea, .wrap input[type="text"] {
    border: 1px solid var(--eco-border) !important;
    border-radius: var(--radius) !important;
    background: var(--eco-card) !important;
    color: var(--eco-text) !important;
}
textarea:focus, input[type="text"]:focus {
    border-color: var(--eco-primary) !important;
    box-shadow: 0 0 0 2px rgba(46,125,80,0.12) !important;
}

/* Fix Gradio 6 Dropdown*/

.gr-dropdown-menu,
.gr-select-dropdown,
.gradio-dropdown-menu,
[role="listbox"] {
    background: #ffffff !important;
    border: 1px solid #dcdcdc !important;
    color: #1c1c1e !important;
}

.gr-dropdown-menu li,
.gr-select-dropdown li,
[role="option"] {
    background: #ffffff !important;
    color: #1c1c1e !important;
    padding: 10px 14px !important;
}

.gr-dropdown-menu li:hover,
.gr-select-dropdown li:hover,
[role="option"]:hover,
[aria-selected="true"] {
    background: #e8f5e9 !important;
    color: #2e7d50 !important;
}

/* Slider */
input[type="range"] {
    accent-color: #2e7d50 !important;
}

input[type="range"]::-webkit-slider-thumb {
    background: #2e7d50 !important;
}

input[type="range"]::-webkit-slider-runnable-track {
    background: #d8e9dc !important;
}

input[type="range"]::-moz-range-thumb {
    background: #2e7d50 !important;
}

input[type="range"]::-moz-range-track {
    background: #d8e9dc !important;
}

/* CheckboxGroup — pills/chips style */
/* ---------- CheckboxGroup ---------- */

.gr-checkboxgroup label,
.gradio-checkbox label {
    background: #f0f7f3 !important;
    border: 1px solid #d6e7da !important;
    color: #1c1c1e !important;
    border-radius: 18px !important;
    padding: 8px 14px !important;
}

.gr-checkboxgroup label:hover,
.gradio-checkbox label:hover {
    background: #e6f3ea !important;
}

.gr-checkboxgroup input:checked + span,
.gradio-checkbox input:checked + span {
    color: white !important;
}

.gr-checkboxgroup label:has(input:checked),
.gradio-checkbox label:has(input:checked) {
    background: #2e7d50 !important;
    border-color: #2e7d50 !important;
}

/* Chatbot */
.message.user {
    background: var(--eco-light) !important;
    border: 1px solid var(--eco-border) !important;
    border-radius: var(--radius) !important;
}
.message.bot {
    background: var(--eco-card) !important;
    border: 1px solid var(--eco-border) !important;
    border-radius: var(--radius) !important;
}
/* Prevent white flash during model thinking */
#chatbot, #chatbot > .wrap, #chatbot > .wrap > .panel {
    background: var(--eco-bg) !important;
}

/* Markdown headings inside tabs */
h3, h2 { color: var(--eco-text) !important; }

/* ── Header ── */
.eco-header {
    background: var(--eco-card);
    border: 1px solid var(--eco-border);
    border-radius: var(--radius);
    padding: 22px 28px;
    margin-bottom: 16px;
    color: var(--eco-text);
    box-shadow: var(--eco-shadow);
}
.eco-header h1 {
    margin: 0 0 4px;
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: -0.3px;
    color: var(--eco-primary);
}
.eco-header p {
    margin: 0;
    font-size: 0.85rem;
    color: var(--eco-muted);
}
.eco-model-badge {
    display: inline-block;
    margin-top: 8px;
    background: var(--eco-light);
    border: 1px solid var(--eco-border);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.73rem;
    font-weight: 600;
    color: var(--eco-primary);
    letter-spacing: 0.3px;
}

/* ── Metric cards ── */
.metric-card {
    background: var(--eco-card);
    border: 1px solid var(--eco-border);
    border-radius: var(--radius);
    padding: 18px 16px;
    text-align: center;
    box-shadow: var(--eco-shadow);
}
.metric-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--eco-primary);
    line-height: 1.1;
}
.metric-label {
    font-size: 0.7rem;
    color: var(--eco-muted);
    margin-top: 3px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    font-weight: 500;
}
.metric-unit {
    font-size: 0.82rem;
    color: var(--eco-muted);
}

/* ── Score ring ── */
.score-ring-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
}
.score-ring {
    width: 80px; height: 80px; border-radius: 50%;
    background: conic-gradient(var(--eco-secondary) calc(var(--pct) * 1%), #eaeaea 0);
    display: flex; align-items: center; justify-content: center;
    position: relative;
}
.score-ring::after {
    content: '';
    width: 60px; height: 60px;
    background: var(--eco-card);
    border-radius: 50%;
    position: absolute;
}
.score-number {
    font-size: 1rem; font-weight: 700;
    color: var(--eco-primary);
    position: relative; z-index: 1;
}
.score-label {
    font-size: 0.68rem;
    color: var(--eco-muted);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.score-count {
    background: var(--eco-light);
    color: var(--eco-primary);
    border: 1px solid var(--eco-border);
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.72rem;
    font-weight: 600;
}

/* ── Recycling output ── */
.recycling-output {
    background: var(--eco-card);
    border: 1px solid var(--eco-border);
    border-radius: var(--radius);
    padding: 14px;
    box-shadow: var(--eco-shadow);
}

/* ── Product cards ── */
.product-card {
    background: var(--eco-card);
    border-left: 3px solid var(--eco-secondary);
    border-radius: 0 var(--radius) var(--radius) 0;
    padding: 10px 14px;
    margin: 5px 0;
    box-shadow: var(--eco-shadow);
    font-size: 0.86rem;
    color: var(--eco-text);
}

/* ── Profile card ── */
.profile-card {
    background: var(--eco-card);
    border: 1px solid var(--eco-border);
    border-radius: var(--radius);
    padding: 14px;
    box-shadow: var(--eco-shadow);
}

/* ── Disclaimer ── */
.disclaimer {
    font-size: 0.72rem;
    color: var(--eco-muted);
    text-align: center;
    padding: 8px 0 4px;
    border-top: 1px solid var(--eco-border);
    margin-top: 10px;
}

/* Agent Mode container */
.gr-form,
.gr-block,
.gr-group {
    background: #fcfcfd !important;
    border: 1px solid #e4e4e7 !important;
}

/* Agent Mode row */
#agent-mode {
    background: #ffffff !important;
    border: 1px solid #e4e4e7 !important;
    border-radius: 8px !important;
    padding: 10px !important;
}

#agent-mode label {
    color: #1c1c1e !important;
}

#agent-mode input:checked {
    accent-color: #2e7d50 !important;
}

#agent-mode-row {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}

/* Checkbox container */
.gr-checkbox {
    background: #ffffff !important;
    border: 1px solid #e4e4e7 !important;
    border-radius: 6px !important;
    padding: 8px 12px !important;
}

/* Checkbox label */
.gr-checkbox label {
    color: #1c1c1e !important;
    font-weight: 500;
}

"""

# ---------------------------------------------------------------------------
# Static HTML — clean light header, no dark-mode button
# ---------------------------------------------------------------------------
HEADER_HTML = """
<div class="eco-header">
  <h1>EcoAgent</h1>
  <p>AI-powered Eco Lifestyle Assistant using IBM Granite 4 H Small and watsonx.ai</p>
</div>
"""

DISCLAIMER_HTML = """
<div class="disclaimer">
  Answers are AI-generated by IBM Granite. Impact figures marked [Lookup] are from IPCC/BEE/CPCB data;
  [Estimate] figures are model-generated. Verify government schemes at official sources.
  Not financial or legal advice.
</div>
"""

# ---------------------------------------------------------------------------
# Quick-action chips for logging eco actions
# ---------------------------------------------------------------------------
ACTION_CHIPS = [
    ("cloth_bags",            "Used cloth bags"),
    ("led_bulbs",             "Switched to LED"),
    ("short_shower",          "Short shower"),
    ("no_plastic_bottles",    "Used steel bottle"),
    ("public_transport",      "Public transport"),
    ("composting",            "Composted waste"),
    ("segregate_waste",       "Segregated waste"),
    ("seasonal_local_produce","Bought local produce"),
    ("line_dry_clothes",      "Line-dried clothes"),
    ("fix_water_leaks",       "Fixed a water leak"),
]

EXAMPLE_PROMPTS = [
    "How can I reduce plastic use in my Indian kitchen?",
    "What government schemes help with solar panel installation in India?",
    "Give me a week-long plan to reduce my family's water usage.",
    "How do I properly dispose of old mobile phones and laptops?",
    "What are the most eco-friendly travel options in a Tier-2 Indian city?",
]


# ---------------------------------------------------------------------------
# Dashboard HTML builder
# ---------------------------------------------------------------------------
def _build_dashboard_html(impact: dict, profile: dict) -> str:
    score = impact.get("eco_score", 0)
    co2 = impact.get("co2_kg_year", 0.0)
    water = impact.get("water_L_day", 0.0)
    waste = impact.get("waste_kg_year", 0.0)
    actions = impact.get("actions_count", 0)
    location = profile.get("location", "India") if profile else "India"
    members = profile.get("members", 1) if profile else 1

    return f"""
<div style="font-family:Inter,sans-serif;color:#1c1c1e;">
  <div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:14px;align-items:stretch;">
    <div class="metric-card" style="flex:1;min-width:150px;">
      <div class="score-ring-wrap">
        <div class="score-ring" style="--pct:{score};">
          <span class="score-number">{score}</span>
        </div>
        <span class="score-label">Eco Score</span>
        <span class="score-count">{actions} action{'s' if actions != 1 else ''} logged</span>
      </div>
    </div>
    <div class="metric-card" style="flex:1;min-width:150px;">
      <div class="metric-value">{members}</div>
      <div class="metric-unit">household member{'s' if members != 1 else ''}</div>
      <div class="metric-label">{location}</div>
    </div>
  </div>
  <p style="font-size:0.76rem;color:#6b6b6f;margin:0 0 8px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">
    Estimated annual savings if logged actions are sustained
  </p>
  <div style="display:flex;gap:10px;flex-wrap:wrap;">
    <div class="metric-card" style="flex:1;min-width:130px;">
      <div class="metric-value">{co2:,.0f}</div>
      <div class="metric-unit">kg CO&#8322;</div>
      <div class="metric-label">Carbon Avoided</div>
    </div>
    <div class="metric-card" style="flex:1;min-width:130px;">
      <div class="metric-value">{water:,.0f}</div>
      <div class="metric-unit">L / day</div>
      <div class="metric-label">Water Saved</div>
    </div>
    <div class="metric-card" style="flex:1;min-width:130px;">
      <div class="metric-value">{waste:,.0f}</div>
      <div class="metric-unit">kg / year</div>
      <div class="metric-label">Waste Diverted</div>
    </div>
  </div>
  {_equivalencies_html(co2, water) if co2 > 0 or water > 0 else ""}
  {_actions_html(impact)}
</div>
"""


def _equivalencies_html(co2: float, water: float) -> str:
    lines = []
    if co2 > 0:
        trees = round(co2 / 21)
        lines.append(f"CO&#8322; savings equivalent to planting <b>{trees} trees</b> per year")
    if water > 0:
        baths = round(water / 150)
        lines.append(f"Water savings equivalent to <b>{baths} bucket baths</b> per day")
    if not lines:
        return ""
    return (
        "<div style='background:#f0f7f3;border:1px solid #e4e4e7;border-radius:6px;"
        "padding:10px 14px;margin-top:12px;font-size:0.82rem;color:#2e7d50;'>"
        + "<br>".join(lines)
        + "</div>"
    )


def _actions_html(impact: dict) -> str:
    count = impact.get("actions_count", 0)
    if count == 0:
        return (
            "<p style='color:#6b6b6f;font-size:0.82rem;margin-top:10px;'>"
            "No actions logged yet. Chat with EcoAgent, then use the action buttons "
            "to log what you have done today.</p>"
        )
    return (
        f"<p style='color:#6b6b6f;font-size:0.80rem;margin-top:10px;'>"
        f"You have logged <b>{count} unique action{'s' if count != 1 else ''}</b> this session. "
        f"Each sustained action compounds over the year.</p>"
    )


# ---------------------------------------------------------------------------
# Recycling products HTML builder
# ---------------------------------------------------------------------------
def _build_products_html(material: str) -> str:
    recs = PRODUCT_RECS.get(material, [])
    if not recs:
        return ""
    items = "".join(f'<div class="product-card">{r}</div>' for r in recs)
    return (
        f"<div style='margin-top:14px;'>"
        f"<p style='font-weight:600;color:#2e7d50;font-size:0.86rem;margin-bottom:4px;'>"
        f"Eco-friendly alternatives and resources for {material}:</p>"
        f"{items}</div>"
    )


# ---------------------------------------------------------------------------
# Profile summary HTML builder
# ---------------------------------------------------------------------------
def _build_profile_html(profile: dict) -> str:
    if not profile or not profile.get("name"):
        return "<p style='color:#6b6b6f;font-size:0.84rem;'>No profile saved yet.</p>"
    habits = profile.get("habits", [])
    habit_list = (
        "<ul style='margin:4px 0;padding-left:18px;font-size:0.82rem;'>"
        + "".join(f"<li>{h}</li>" for h in habits)
        + "</ul>"
        if habits
        else "<p style='color:#6b6b6f;font-size:0.82rem;'>No habits recorded.</p>"
    )
    return f"""
<div class="profile-card">
  <p style="font-size:0.93rem;font-weight:700;color:#2e7d50;margin:0 0 6px;">{profile['name']}</p>
  <p style="font-size:0.82rem;margin:2px 0;"><b>Location:</b> {profile.get('location','—')}</p>
  <p style="font-size:0.82rem;margin:2px 0;"><b>Members:</b> {profile.get('members',1)}</p>
  <p style="font-size:0.82rem;margin:6px 0 2px;"><b>Current eco habits:</b></p>
  {habit_list}
</div>
"""


# ---------------------------------------------------------------------------
# Core chat callback
# ---------------------------------------------------------------------------
def chat_submit(
    message: str,
    history: list,
    profile_state: dict,
    actions_state: list,
    agent_mode: bool = False,
):
    """Handle a user message: call Granite, update history.

    Gradio 6.x passes history as list[dict] where content is a list of
    content blocks: [{"role": "user", "content": [{"type": "text", "text": "..."}]}].
    We extract plain text for the API call and return structured blocks for display.

    When agent_mode is True, uses the agentic loop with tool calls.
    """
    if not message or not message.strip():
        return history, profile_state, actions_state, _score_html(actions_state), ""

    # Gradio 6 delivers history with structured content blocks
    # Extract plain text for the watsonx API call
    messages: list[dict] = []
    for turn in history:
        role = turn.get("role", "")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            # Content can be a string or a list of content blocks
            if isinstance(content, list):
                text = " ".join(
                    block.get("text", "") for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                )
            else:
                text = str(content)
            if text:
                messages.append({"role": role, "content": text})

    messages.append({"role": "user", "content": message})

    tool_display = ""

    try:
        if agent_mode:
            # Use agentic loop with tools
            reply, tool_calls = agent_loop(message, profile_state, messages[:-1])
            tool_display = format_tool_calls(tool_calls)
        else:
            reply = get_eco_answer(messages, profile_state)
    except EnvironmentError as exc:
        reply = (
            "**Setup required.**\n\n"
            f"{exc}\n\n"
            "Please set your credentials in `.env` and restart the app."
        )
    except RuntimeError as exc:
        logger.error("watsonx error: %s", exc)
        reply = (
            "**EcoAgent is temporarily unavailable.**\n\n"
            f"Error: {exc}\n\n"
            "Please check your internet connection or try again in a moment."
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error in chat_submit")
        reply = f"An unexpected error occurred ({type(exc).__name__}). Please try again."

    # Append in Gradio 6 structured content block format
    history = history + [
        {"role": "user", "content": [{"type": "text", "text": message}]},
        {"role": "assistant", "content": [{"type": "text", "text": reply}]},
    ]
    return history, profile_state, actions_state, _score_html(actions_state), tool_display


def _score_html(actions_state: list) -> str:
    impact = compute_session_impact(actions_state)
    score = impact["eco_score"]
    count = impact["actions_count"]
    return (
        f"<div class='score-ring-wrap' style='padding:6px 0;'>"
        f"<div class='score-ring' style='--pct:{score};width:72px;height:72px;'>"
        f"<span class='score-number'>{score}</span></div>"
        f"<span class='score-label'>Eco Score</span>"
        f"<span class='score-count'>{count} action{'s' if count != 1 else ''}</span></div>"
    )


def log_action(slug: str, actions_state: list) -> tuple[list, str]:
    """Toggle an action slug in the logged actions list."""
    if slug in actions_state:
        actions_state = [a for a in actions_state if a != slug]
    else:
        actions_state = actions_state + [slug]
    return actions_state, _score_html(actions_state)


def update_dashboard(actions_state: list, profile_state: dict) -> str:
    members = profile_state.get("members", 1) if profile_state else 1
    impact = compute_session_impact(actions_state, members)
    return _build_dashboard_html(impact, profile_state or {})


def _search_local_recycling(material: str, city: str) -> str:
    """Search for local recycling centers and latest info using web search."""
    from tools import execute_tool
    
    # Build search queries for comprehensive results
    queries = [
        f"{material} recycling center {city} India",
        f"{material} waste disposal {city} India 2026",
    ]
    
    all_results = []
    for query in queries:
        try:
            result = execute_tool("web_search", {"query": query})
            if result and "No results" not in result and "Error" not in result:
                # Extract just the search results, not the header
                lines = result.split("\n")
                # Find the numbered results
                for line in lines:
                    if line.strip().startswith("1.") or line.strip().startswith("2.") or line.strip().startswith("3."):
                        all_results.append(line.strip())
                break  # Stop after first successful query
        except Exception:
            continue
    
    if all_results:
        return (
            f"\n\n---\n\n"
            f"### Local Recycling Options in {city}\n\n"
            f"{chr(10).join(all_results[:5])}\n\n"
            f"*For the most current information, please verify directly with these centers.*"
        )
    else:
        return (
            f"\n\n---\n\n"
            f"### Local Recycling Options in {city}\n\n"
            f"*Web search did not return specific results for {material} recycling in {city}. "
            f"Please contact your local municipal corporation or waste management authority for current information.*"
        )


def get_recycling(material: str, city: str) -> tuple[str, str, str]:
    """Fetch guide + local info + product recs for a material/city combination.
    
    Returns:
        Tuple of (guide_markdown, local_info_markdown, products_html)
    """
    if not material or not city:
        return "Please select both a material and a city.", "", ""
    
    # 1. Get LLM-generated guide (existing)
    try:
        guide = get_recycling_guide(material, city)
    except EnvironmentError as exc:
        guide = f"Setup required: {exc}"
    except RuntimeError as exc:
        guide = f"Could not fetch guide: {exc}"
    
    # 2. Web search for local recycling info (NEW)
    local_info = _search_local_recycling(material, city)
    
    # 3. Product recommendations (existing)
    products_html = _build_products_html(material)
    
    return guide, local_info, products_html


def save_profile(
    name: str,
    location: str,
    members: int,
    habits: list,
    actions_state: list,
) -> tuple[dict, str, str]:
    """Save household profile and return updated state + HTML summary."""
    profile = {
        "name": name.strip() if name else "My Household",
        "location": location,
        "members": int(members),
        "habits": habits,
    }
    summary = _build_profile_html(profile)
    dashboard = update_dashboard(actions_state, profile)
    return profile, summary, dashboard


# ===========================================================================
#  GRADIO BLOCKS APP
# ===========================================================================
with gr.Blocks(title="EcoAgent — Eco Lifestyle Assistant") as demo:

    profile_state = gr.State({})
    actions_state = gr.State([])

    gr.HTML(HEADER_HTML)

    with gr.Tabs(elem_classes="tab-nav"):

        # ================================================================
        #  TAB 1: CHAT
        # ================================================================
        with gr.Tab("Chat"):
            with gr.Row():
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(
                        height=430,
                        show_label=False,
                        elem_id="chatbot",
                        placeholder=(
                            "<div style='text-align:center;padding:40px 20px;background:#fcfcfd;border-radius:6px;'>"
                            "<p style='font-size:1rem;font-weight:600;margin:0 0 6px;color:#2e7d50;'>Welcome to EcoAgent</p>"
                            "<p style='font-size:0.84rem;margin:0;color:#4a4a4e;'>Ask me anything about sustainable living, "
                            "eco travel, recycling, or Indian government green schemes.</p>"
                            "</div>"
                        ),
                    )
                    # Agent Mode toggle and tool call display
                    with gr.Row(elem_id="agent-mode-row"):
                        agent_mode_toggle = gr.Checkbox(
                            label="Agent Mode",
                            value=False,
                            info="Multi-step reasoning with tools",
                            scale=1,
                            elem_id="agent-mode",
                        )
                    tool_calls_display = gr.Markdown(
                        "",
                        visible=True,
                        label="Tool Calls",
                    )
                    with gr.Row():
                        msg_input = gr.Textbox(
                            placeholder="Ask EcoAgent a question...",
                            show_label=False,
                            scale=5,
                            lines=1,
                        )
                        send_btn = gr.Button("Send",variant="primary", scale=1)

                    gr.Markdown("**Quick start questions:**")
                    with gr.Row():
                        for prompt in EXAMPLE_PROMPTS[:3]:
                            ex_btn = gr.Button(prompt, size="sm", variant="secondary")
                            ex_btn.click(lambda p=prompt: p, outputs=msg_input)
                    with gr.Row():
                        for prompt in EXAMPLE_PROMPTS[3:]:
                            ex_btn = gr.Button(prompt, size="sm", variant="secondary")
                            ex_btn.click(lambda p=prompt: p, outputs=msg_input)

                with gr.Column(scale=1, min_width=190):
                    score_display = gr.HTML(_score_html([]))
                    gr.Markdown("**Log today's actions:**")
                    chip_btns = []
                    for slug, label in ACTION_CHIPS:
                        btn = gr.Button(label, size="sm", variant="secondary")
                        chip_btns.append((slug, btn))

            def _submit(message, history, profile, actions, agent_mode):
                return chat_submit(message, history, profile, actions, agent_mode)

            send_btn.click(
                _submit,
                inputs=[msg_input, chatbot, profile_state, actions_state, agent_mode_toggle],
                outputs=[chatbot, profile_state, actions_state, score_display, tool_calls_display],
            ).then(lambda: "", outputs=msg_input)

            msg_input.submit(
                _submit,
                inputs=[msg_input, chatbot, profile_state, actions_state, agent_mode_toggle],
                outputs=[chatbot, profile_state, actions_state, score_display, tool_calls_display],
            ).then(lambda: "", outputs=msg_input)

            for slug, btn in chip_btns:
                btn.click(
                    lambda a, s=slug: log_action(s, a),
                    inputs=[actions_state],
                    outputs=[actions_state, score_display],
                )

        # ================================================================
        #  TAB 2: DASHBOARD
        # ================================================================
        with gr.Tab("Dashboard"):
            gr.Markdown(
                "### Your Eco Impact Dashboard\n"
                "Log actions in the Chat tab to see your estimated savings grow."
            )
            dashboard_html = gr.HTML(
                _build_dashboard_html(compute_session_impact([]), {}),
            )
            refresh_btn = gr.Button("Refresh Dashboard", variant="secondary")
            refresh_btn.click(
                update_dashboard,
                inputs=[actions_state, profile_state],
                outputs=dashboard_html,
            )

        # ================================================================
        #  TAB 3: RECYCLING GUIDE
        # ================================================================
        with gr.Tab("Recycling Guide"):
            gr.Markdown(
                "### Local Recycling Guide\n"
                "Select a waste material and your city to get India-specific "
                "recycling instructions and eco-friendly product alternatives.\n\n"
                "*Includes web search for local recycling centers in your city.*"
            )
            with gr.Row():
                material_dd = gr.Dropdown(
                    choices=list(PRODUCT_RECS.keys()),
                    label="Waste Material",
                    value="E-waste",
                    scale=1,
                )
                city_dd = gr.Dropdown(
                    choices=INDIAN_CITIES,
                    label="Your City",
                    value="Bangalore",
                    scale=1,
                )
                guide_btn = gr.Button("Get Recycling Guide", variant="primary", scale=1)

            guide_output = gr.Markdown(
                "*Select a material and city above, then click Get Recycling Guide.*",
                label="Recycling Instructions",
                elem_classes="recycling-output",
            )
            local_output = gr.Markdown(
                "",
                label="Local Recycling Centers",
                elem_classes="recycling-output",
            )
            products_output = gr.HTML("", label="Eco-Friendly Alternatives")

            guide_btn.click(
                get_recycling,
                inputs=[material_dd, city_dd],
                outputs=[guide_output, local_output, products_output],
            )
            material_dd.change(
                lambda m: _build_products_html(m),
                inputs=material_dd,
                outputs=products_output,
            )

        # ================================================================
        #  TAB 4: PROFILE
        # ================================================================
        with gr.Tab("Profile"):
            gr.Markdown(
                "### Household Profile\n"
                "Set your household details so EcoAgent can give personalised, "
                "family-scale advice relevant to your location."
            )
            with gr.Row():
                with gr.Column(scale=2):
                    hh_name = gr.Textbox(
                        label="Household Name",
                        placeholder="e.g. The Sharma Family",
                    )
                    with gr.Row():
                        hh_location = gr.Dropdown(
                            choices=INDIAN_CITIES + [
                                "Other - North India", "Other - South India",
                                "Other - East India", "Other - West India",
                                "Rural area",
                            ],
                            label="City / Location",
                            value="Bangalore",
                            scale=2,
                        )
                        hh_members = gr.Slider(
                            minimum=1, maximum=12, value=4, step=1,
                            label="Household Members",
                            scale=2,
                        )
                    hh_habits = gr.CheckboxGroup(
                        choices=[
                            "Vegetarian / vegan diet",
                            "Use public transport regularly",
                            "Have solar panels installed",
                            "Compost kitchen waste",
                            "Use cloth / jute bags",
                            "Avoid single-use plastics",
                            "Harvest rainwater",
                            "Segregate wet and dry waste",
                            "Use LED bulbs throughout",
                            "Grow some food at home",
                        ],
                        label="Current Eco Habits (select all that apply)",
                    )
                    save_btn = gr.Button("Save Profile", variant="primary")

                with gr.Column(scale=1):
                    profile_summary = gr.HTML(
                        "<p style='color:#6b6b6f;font-size:0.84rem;'>"
                        "Fill in your details and click Save Profile.</p>",
                    )

            # Save updates profile_state, profile HTML, and dashboard
            save_btn.click(
                save_profile,
                inputs=[hh_name, hh_location, hh_members, hh_habits, actions_state],
                outputs=[profile_state, profile_summary, dashboard_html],
            )

    # ── Footer disclaimer ──────────────────────────────────────────────────
    gr.HTML(DISCLAIMER_HTML)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    eco_theme = gr.themes.Soft(
        primary_hue="green",
        secondary_hue="emerald",
        neutral_hue="gray",        
        font="Inter, system-ui, sans-serif",
        font_mono="Fira Code, monospace",
    ).set(
        body_background_fill="#fcfcfd",
        body_background_fill_dark="#fcfcfd",
        body_text_color="#1c1c1e",
        body_text_color_dark="#1c1c1e",
        block_background_fill="#ffffff",
        block_border_color="#e4e4e7",
        block_label_text_color="#4a4a4e",
        block_title_text_color="#1c1c1e",
        input_background_fill="#ffffff",
        input_border_color="#e4e4e7",
        input_border_color_focus="#2e7d50",
        button_primary_background_fill="#2e7d50",
        button_primary_background_fill_hover="#256a42",
        button_primary_border_color="#2e7d50",
        button_primary_text_color="#ffffff",
        button_secondary_background_fill="#f0f7f3",
        button_secondary_background_fill_hover="#e4eff0",
        button_secondary_border_color="#e4e4e7",
        button_secondary_text_color="#1c1c1e",
        checkbox_background_color="#ffffff",
        checkbox_background_color_selected="#2e7d50",
        checkbox_border_color="#e4e4e7",
        checkbox_border_color_selected="#2e7d50",
        checkbox_label_text_color="#1c1c1e",
        checkbox_label_text_color_selected="#ffffff",
        checkbox_label_background_fill="#f0f7f3",
        checkbox_label_background_fill_hover="#e4eff0",
        checkbox_label_background_fill_selected="#2e7d50",
        checkbox_label_border_color="#e4e4e7",
        checkbox_label_border_color_selected="#2e7d50",
        checkbox_label_border_width="1px",
        slider_color="#2e7d50",
    )

    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        share=False,
        theme=eco_theme,
        css=CUSTOM_CSS,
    )
