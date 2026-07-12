"""
watsonx_client.py
-----------------
IBM watsonx.ai SDK client for EcoAgent.

Provides:
  - AGENT_INSTRUCTIONS  : Editable agent behaviour / persona block
  - IMPACT_TABLE        : CO2/water/waste lookup for 20 common eco actions
  - get_eco_answer()    : Multi-turn chat via IBM Granite
  - get_recycling_guide(): Single-turn recycling lookup for Indian cities

Region: eu-de (Frankfurt)  |  Model: ibm/granite-4-h-small
"""

import os
import logging
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load credentials from .env
# ---------------------------------------------------------------------------
load_dotenv(".env")

logger = logging.getLogger(__name__)

# ===========================================================================
#  AGENT INSTRUCTIONS
#  Edit this block to customise persona, tone, focus areas, and rules.
# ===========================================================================
AGENT_INSTRUCTIONS = """
You are EcoAgent — a friendly, knowledgeable, and action-focused eco lifestyle
advisor specialised in the Indian context. Your goal is to help Indian households
live more sustainably through practical, affordable, and culturally relevant advice.

## Persona & Tone
- Warm, encouraging, and non-preachy
- Concise: lead with the action, not the theory
- Use simple English; avoid jargon
- Celebrate small wins — every action counts

## Answer Structure (ALWAYS follow this)
1. **Quick Tip** (1–2 sentences): the specific action the user should take
2. **Why it Matters** (1 sentence): the environmental/health/cost benefit
3. **Impact** (1 line): if the action is in the impact table, state the exact figure
   and label it "[Lookup]"; otherwise estimate and label it "[Estimate]"
4. **Optional Resource** (1 line): a relevant Indian scheme, website, or product
   — only include if genuinely useful, never invent URLs

## Sustainability Focus Areas
- Plastic reduction and single-use alternatives
- Energy efficiency (LED, appliances, solar)
- Water conservation (short showers, rainwater harvesting, drip irrigation)
- Eco-friendly travel (public transport, cycling, EVs under FAME scheme)
- Food choices (reduce meat, local/seasonal produce, reduce food waste)
- Waste management (segregation, composting, e-waste disposal)

## India-Specific Context
- Always reference Indian government schemes where applicable:
    * PM Surya Ghar Muft Bijli Yojana (rooftop solar, up to 300 units free/month)
    * FAME II / PM e-DRIVE (EV subsidies for 2W and 3W vehicles)
    * Swachh Bharat Mission (waste management, ODF)
    * Jal Jeevan Mission (clean water, conservation)
    * UJALA scheme (LED bulb distribution at subsidised prices)
    * National Biogas Programme (biogas plants for households)
- Reference Indian brands and local alternatives where helpful
  (e.g., Bamboo India, Bare Necessities, The Better India marketplace)
- Recycling norms vary by city — acknowledge this and advise accordingly
- Common Indian household practices to acknowledge:
    * Pressure cookers, clay pots, steel utensils (already eco-friendly)
    * Festivals with high waste (Diwali crackers, Holi colours)
    * Joint family structures → household-level advice is very relevant

## Safety & Accuracy Rules
- NEVER invent statistics or make up government scheme details
- If you are not sure of a specific number, say "approximately" and label [Estimate]
- Do not recommend products with specific prices (prices change)
- If the user's question is outside your eco domain, politely redirect
- Do not provide medical, legal, or financial advice

## Household Context
When a household profile is provided, tailor advice to:
- The number of family members (scale savings accordingly)
- Current habits (avoid advising things they already do)
- Location (city-specific recycling facilities, local schemes)
- Specific constraints (e.g., rented accommodation → skip solar panel advice)
"""

# ===========================================================================
#  CARBON / RESOURCE IMPACT LOOKUP TABLE
#  Sources: IPCC AR6, EPA GHG equivalencies, BEE India, WRI India reports,
#           Central Pollution Control Board (CPCB) India data.
#  Each action maps to annual savings for ONE person unless noted.
# ===========================================================================
IMPACT_TABLE: dict[str, dict] = {
    "cloth_bags": {
        "label": "Switch to cloth/jute bags",
        "co2_kg_year": 3.0,
        "water_L_day": 0,
        "waste_kg_year": 5.0,
        "source": "Lookup",
        "note": "Avoids ~150 plastic bags/year @ 20g CO2 each",
    },
    "led_bulbs": {
        "label": "Replace all bulbs with LED",
        "co2_kg_year": 45.0,
        "water_L_day": 0,
        "waste_kg_year": 0,
        "source": "Lookup",
        "note": "Avg Indian home 8 bulbs; 60W→9W LED, 6h/day, Indian grid 0.82 kg CO2/kWh",
    },
    "solar_panels": {
        "label": "Install rooftop solar (1 kW)",
        "co2_kg_year": 820.0,
        "water_L_day": 0,
        "waste_kg_year": 0,
        "source": "Lookup",
        "note": "1 kW @ 4.5 peak sun hours, 0.82 kg CO2/kWh displaced",
    },
    "composting": {
        "label": "Compost kitchen waste",
        "co2_kg_year": 120.0,
        "water_L_day": 0,
        "waste_kg_year": 150.0,
        "source": "Lookup",
        "note": "Avg 400g/day organic waste; avoids landfill methane",
    },
    "public_transport": {
        "label": "Use public transport instead of car",
        "co2_kg_year": 1200.0,
        "water_L_day": 0,
        "waste_kg_year": 0,
        "source": "Lookup",
        "note": "20 km/day commute; 180g CO2/km (petrol car) vs 30g CO2/km (metro/bus)",
    },
    "short_shower": {
        "label": "Reduce shower time by 2 minutes",
        "co2_kg_year": 12.0,
        "water_L_day": 20.0,
        "waste_kg_year": 0,
        "source": "Lookup",
        "note": "10 L/min showerhead; 2 min × 10 L = 20 L/day saved",
    },
    "rainwater_harvesting": {
        "label": "Install rainwater harvesting",
        "co2_kg_year": 8.0,
        "water_L_day": 80.0,
        "waste_kg_year": 0,
        "source": "Lookup",
        "note": "Avg 100 sqm roof; 800mm annual rainfall region",
    },
    "vegetarian_diet": {
        "label": "Switch to vegetarian diet",
        "co2_kg_year": 550.0,
        "water_L_day": 800.0,
        "waste_kg_year": 0,
        "source": "Lookup",
        "note": "Meat diet 2.5 kg CO2/day vs veg 1.0 kg CO2/day; water footprint halved",
    },
    "no_plastic_bottles": {
        "label": "Use refillable steel/copper water bottle",
        "co2_kg_year": 6.5,
        "water_L_day": 0,
        "waste_kg_year": 8.0,
        "source": "Lookup",
        "note": "Avoids ~500 plastic bottles/year; 13g CO2 per PET bottle",
    },
    "drip_irrigation": {
        "label": "Switch to drip irrigation (garden/farm)",
        "co2_kg_year": 0,
        "water_L_day": 200.0,
        "waste_kg_year": 0,
        "source": "Lookup",
        "note": "Drip uses 30–50% less water than flood irrigation; 40% saving assumed",
    },
    "smart_powerstrip": {
        "label": "Use smart power strip / switch off standby",
        "co2_kg_year": 28.0,
        "water_L_day": 0,
        "waste_kg_year": 0,
        "source": "Lookup",
        "note": "Standby power ~10% of home electricity; 350 kWh/year at 0.82 kg CO2/kWh",
    },
    "electric_two_wheeler": {
        "label": "Switch from petrol 2W to electric",
        "co2_kg_year": 380.0,
        "water_L_day": 0,
        "waste_kg_year": 0,
        "source": "Lookup",
        "note": "30 km/day; petrol scooter 70g CO2/km vs EV 15g CO2/km (Indian grid)",
    },
    "reusable_bags_produce": {
        "label": "Use mesh bags for fruits/vegetables",
        "co2_kg_year": 1.5,
        "water_L_day": 0,
        "waste_kg_year": 3.0,
        "source": "Lookup",
        "note": "Avoids ~150 thin plastic produce bags/year",
    },
    "fix_water_leaks": {
        "label": "Fix dripping taps and leaking pipes",
        "co2_kg_year": 3.0,
        "water_L_day": 30.0,
        "waste_kg_year": 0,
        "source": "Lookup",
        "note": "A dripping tap wastes ~15 L/day; 2 taps assumed",
    },
    "line_dry_clothes": {
        "label": "Line-dry clothes instead of electric dryer",
        "co2_kg_year": 100.0,
        "water_L_day": 0,
        "waste_kg_year": 0,
        "source": "Lookup",
        "note": "Electric dryer ~3 kWh/load, 3 loads/week; 0.82 kg CO2/kWh",
    },
    "seasonal_local_produce": {
        "label": "Buy seasonal and locally grown produce",
        "co2_kg_year": 60.0,
        "water_L_day": 0,
        "waste_kg_year": 0,
        "source": "Lookup",
        "note": "Reduces food transport emissions; avg 200g CO2/km per tonne",
    },
    "segregate_waste": {
        "label": "Segregate wet/dry/hazardous waste at home",
        "co2_kg_year": 90.0,
        "water_L_day": 0,
        "waste_kg_year": 200.0,
        "source": "Lookup",
        "note": "Enables recycling of 55% of household waste; avoids landfill methane",
    },
    "pressure_cooker": {
        "label": "Use pressure cooker instead of open pot",
        "co2_kg_year": 18.0,
        "water_L_day": 0,
        "waste_kg_year": 0,
        "source": "Lookup",
        "note": "70% faster cooking → 70% less LPG; 1 kg LPG = 3 kg CO2",
    },
    "no_single_use_plastic": {
        "label": "Eliminate single-use plastics (cutlery, straws, cups)",
        "co2_kg_year": 5.0,
        "water_L_day": 0,
        "waste_kg_year": 10.0,
        "source": "Lookup",
        "note": "India banned SUP Jul 2022; alternatives: bamboo, steel, areca leaf",
    },
    "organic_farming": {
        "label": "Switch to organic / natural farming inputs",
        "co2_kg_year": 200.0,
        "water_L_day": 50.0,
        "waste_kg_year": 0,
        "source": "Estimate",
        "note": "Avoids synthetic fertiliser (4 kg CO2 per kg N); varies widely by crop",
    },
}


# ===========================================================================
#  ECO-FRIENDLY PRODUCT RECOMMENDATIONS BY CATEGORY
#  (Used in the Recycling & Products tab)
# ===========================================================================
PRODUCT_RECS: dict[str, list[str]] = {
    "Plastic": [
        "Bamboo India — bamboo toothbrushes, combs, straws",
        "Bare Necessities — zero-waste personal care products",
        "StorTi — stainless steel food storage containers",
        "Paperwala — kraft paper bags for shopping",
    ],
    "Paper": [
        "Use both sides before recycling",
        "Switch to digital billing to reduce paper waste",
        "Recycled paper products: Haathi Chaap (elephant-dung paper crafts)",
        "Paper log briquettes for biomass energy",
    ],
    "Glass": [
        "Milkbasket / local dairy — refillable glass bottles",
        "Borosil glass containers as plastic-free food storage",
        "Reuse glass jars for storage (zero cost!)",
    ],
    "E-waste": [
        "E-Parisaraa — India's first e-waste recycler (Bangalore)",
        "Karma Recycling — e-waste pick-up across major Indian cities",
        "Attero Recycling — certified e-waste management",
        "Check manufacturer take-back: Dell, HP, Samsung have return programmes",
    ],
    "Metal": [
        "Scrap dealers (kabadiwala) for steel, copper, aluminium",
        "Steel Recycling Institute of India (SRII) facility locator",
        "Avoid single-use aluminium foil; use beeswax wraps instead",
    ],
    "Organic": [
        "Daily Dump — home composting kits (Bangalore, ships PAN India)",
        "Kambha composting pots — traditional Indian clay composters",
        "SBI (Solid Biomass India) — biogas kits for kitchen waste",
        "Vermi-composting kits via TNAU / KVK agricultural centres",
    ],
    "Batteries": [
        "Exide / Amaron authorised collection centres for lead-acid batteries",
        "Panasonic / Duracell — collect at Croma / Reliance Digital stores",
        "Switch to rechargeable NiMH batteries (Envie brand India)",
        "Solar lanterns: Greenlight Planet / Minda (avoid disposables)",
    ],
    "Clothing": [
        "ThriftMyFashion / The Loom (pre-owned clothing platforms)",
        "Ekgaon — organic cotton and natural dye clothing",
        "Upasana Design Studio — sustainable handloom fashion",
        "Goonj — donate old clothes for rural upcycling",
        "Repair before discarding: local darzi (tailor) network",
    ],
}

# Indian cities for recycling guide
INDIAN_CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai",
    "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
    "Kochi", "Chandigarh", "Bhopal", "Indore", "Surat",
]

# ===========================================================================
#  watsonx.ai CLIENT SETUP
#  Uses APIClient pattern with set_default_project(), matching IBM example code.
# ===========================================================================
_WATSONX_API_KEY  = os.environ.get("WATSONX_API_KEY", "")
_WATSONX_URL      = os.environ.get("WATSONX_URL", "https://eu-de.ml.cloud.ibm.com")
_WATSONX_PROJECT_ID = os.environ.get("WATSONX_PROJECT_ID", "")

# IBM Granite 4 H Small — official watsonx.ai model ID for the Granite 4 "H" (tiny) series.
# The SDK fetches the live model list at runtime; no enum entry is required.
# Fallback to Granite 3.3 if the project plan does not include Granite 4 access.
_MODEL_ID_PRIMARY  = "ibm/granite-4-h-small"
_MODEL_ID_FALLBACK = "ibm/granite-3-3-8b-instruct"

_model = None      # ModelInference instance — lazy-initialised on first call
_api_client = None # APIClient instance — reused across calls


def _get_model():
    """Return a cached ModelInference instance, initialising on first call.

    Uses the APIClient + set_default_project() pattern so the client is
    authenticated once and reused for every subsequent chat call.
    """
    global _model, _api_client
    if _model is not None:
        return _model

    if not _WATSONX_API_KEY:
        raise EnvironmentError(
            "WATSONX_API_KEY is not set. "
            "Add it to your .env file (see .env.example)."
        )
    if not _WATSONX_PROJECT_ID:
        raise EnvironmentError(
            "WATSONX_PROJECT_ID is not set.\n"
            "How to get it:\n"
            "  1. Go to https://eu-de.dataplatform.cloud.ibm.com\n"
            "  2. Open your project -> Manage tab -> General -> copy Project ID\n"
            "  3. Add WATSONX_PROJECT_ID=<uuid> to your .env file"
        )

    try:
        from ibm_watsonx_ai import APIClient, Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference
    except ImportError as exc:
        raise ImportError(
            "ibm-watsonx-ai is not installed. Run: pip install ibm-watsonx-ai"
        ) from exc

    # Build credentials and APIClient — mirrors the IBM example code exactly:
    #   credentials = Credentials(url=..., api_key=...)
    #   api_client  = APIClient(credentials, space_id)
    #   api_client.set.default_project(space_id)
    credentials = Credentials(url=_WATSONX_URL, api_key=_WATSONX_API_KEY)
    _api_client = APIClient(credentials, _WATSONX_PROJECT_ID)
    _api_client.set.default_project(_WATSONX_PROJECT_ID)
    logger.info("watsonx APIClient initialised (project=%s)", _WATSONX_PROJECT_ID)

    # Try primary model, fall back silently if unavailable in this project
    for model_id in (_MODEL_ID_PRIMARY, _MODEL_ID_FALLBACK):
        try:
            _model = ModelInference(
                model_id=model_id,
                api_client=_api_client,
            )
            logger.info("watsonx ModelInference initialised: %s", model_id)
            return _model
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Model %s unavailable (%s) — trying fallback", model_id, exc
            )

    raise RuntimeError(
        f"Neither {_MODEL_ID_PRIMARY!r} nor {_MODEL_ID_FALLBACK!r} could be "
        "initialised. Check your watsonx.ai project has access to these models."
    )


def _build_system_prompt(profile: dict) -> str:
    """Inject household profile context into the system message."""
    profile_block = ""
    if profile:
        members = profile.get("members", 1)
        location = profile.get("location", "India")
        habits = profile.get("habits", [])
        name = profile.get("name", "")
        profile_block = (
            f"\n\n## Current Household Profile\n"
            f"- Household name: {name or 'Not provided'}\n"
            f"- Location: {location}\n"
            f"- Members: {members}\n"
            f"- Current eco habits: {', '.join(habits) if habits else 'None specified'}\n"
            f"\nScale all impact estimates to {members} person(s) where relevant. "
            f"Do not re-recommend habits the household already practises."
        )
    return AGENT_INSTRUCTIONS.strip() + profile_block


def get_eco_answer(messages: list[dict], profile: dict | None = None) -> str:
    """Send a multi-turn conversation to Granite and return the reply.

    Args:
        messages: List of {"role": "user"|"assistant", "content": str} dicts.
                  Do NOT include a system message — this function prepends it.
        profile:  Optional household profile dict from the Profile tab.

    Returns:
        The assistant's reply as a plain string.

    Raises:
        EnvironmentError: Missing credentials (caught by app.py).
        RuntimeError:     API call failure (caught by app.py).
    """
    model = _get_model()
    system_prompt = _build_system_prompt(profile or {})

    full_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        response = model.chat(
            messages=full_messages,
            params={
                "max_tokens": 800,
                "temperature": 0.7,
                "top_p": 0.95,
            },
        )
        return response["choices"][0]["message"]["content"].strip()
    except KeyError as exc:
        raise RuntimeError(
            f"Unexpected response format from watsonx.ai: missing key {exc}. "
            f"Raw response: {str(response)[:300]}"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"watsonx.ai call failed: {exc}") from exc


def get_recycling_guide(material: str, city: str) -> str:
    """Ask Granite for recycling instructions for a specific material and city.

    Args:
        material: One of the material categories (e.g. "E-waste", "Plastic").
        city:     Indian city name for local context.

    Returns:
        Formatted recycling guide as a markdown string.
    """
    prompt = (
        f"Provide a practical recycling guide for **{material}** waste in {city}, India. "
        f"Include:\n"
        f"1. How to prepare/segregate this waste at home\n"
        f"2. Where to drop it off or how to get it collected in {city}\n"
        f"3. What happens to it after collection (briefly)\n"
        f"4. One eco-friendly alternative to reduce this waste type\n"
        f"Keep the response concise, practical, and India-specific. "
        f"Use bullet points. Label any uncertain details as [Estimate]."
    )
    model = _get_model()
    try:
        response = model.chat(
            messages=[
                {"role": "system", "content": AGENT_INSTRUCTIONS.strip()},
                {"role": "user", "content": prompt},
            ],
            params={"max_tokens": 500, "temperature": 0.4},
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Recycling guide call failed: {exc}") from exc


def compute_session_impact(logged_actions: list[str], members: int = 1) -> dict:
    """Aggregate CO2/water/waste savings for a list of logged action slugs.

    Args:
        logged_actions: List of action slug strings from IMPACT_TABLE keys.
        members:        Household size to scale savings.

    Returns:
        Dict with keys: co2_kg_year, water_L_day, waste_kg_year, eco_score (0–100).
    """
    co2 = 0.0
    water = 0.0
    waste = 0.0
    unique = set(logged_actions)

    for slug in unique:
        entry = IMPACT_TABLE.get(slug)
        if entry:
            co2 += entry.get("co2_kg_year", 0) * members
            water += entry.get("water_L_day", 0) * members
            waste += entry.get("waste_kg_year", 0) * members

    eco_score = min(100, len(unique) * 8)  # 8 pts per unique action, cap 100
    return {
        "co2_kg_year": round(co2, 1),
        "water_L_day": round(water, 1),
        "waste_kg_year": round(waste, 1),
        "eco_score": eco_score,
        "actions_count": len(unique),
    }
