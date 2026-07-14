"""
tools.py
--------
Tool registry and executor for EcoAgent's agentic mode.

Provides:
  - TOOLS           : List of tool definitions (JSON Schema format)
  - execute_tool()  : Routes tool calls to appropriate functions
  - SCHEMES_DB      : Static lookup for Indian government eco schemes
"""

import os
import logging
from datetime import datetime
from typing import Any

# Fix SSL certificate path before importing watsonx_client
if "SSL_CERT_FILE" not in os.environ or not os.path.isfile(os.environ.get("SSL_CERT_FILE", "")):
    try:
        import certifi
        os.environ["SSL_CERT_FILE"] = certifi.where()
        os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
    except ImportError:
        pass

from watsonx_client import (
    IMPACT_TABLE,
    INDIAN_CITIES,
    compute_session_impact,
    get_recycling_guide,
    _get_model,
    AGENT_INSTRUCTIONS,
)

logger = logging.getLogger(__name__)

# ===========================================================================
#  TOOL DEFINITIONS
#  Format compatible with IBM Granite function calling / tool use.
# ===========================================================================
TOOLS: list[dict[str, Any]] = [
    {
        "name": "calculate_impact",
        "description": (
            "Calculate CO2 (kg/year), water (L/day), and waste (kg/year) savings "
            "for one or more eco actions. Use when the user asks about environmental "
            "impact, wants numbers, or compares actions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action_slug": {
                    "type": "string",
                    "description": (
                        "Action identifier from the impact table. "
                        "Valid slugs: cloth_bags, led_bulbs, solar_panels, composting, "
                        "public_transport, short_shower, rainwater_harvesting, "
                        "vegetarian_diet, no_plastic_bottles, drip_irrigation, "
                        "smart_powerstrip, electric_two_wheeler, reusable_bags_produce, "
                        "fix_water_leaks, line_dry_clothes, seasonal_local_produce, "
                        "segregate_waste, pressure_cooker, no_single_use_plastic, "
                        "organic_farming"
                    ),
                },
                "members": {
                    "type": "integer",
                    "description": "Number of household members to scale savings. Default: 1",
                },
            },
            "required": ["action_slug"],
        },
    },
    {
        "name": "get_recycling_guide",
        "description": (
            "Get recycling instructions for a specific material in an Indian city. "
            "Use when the user asks how to recycle something, where to dispose of waste, "
            "or wants recycling guidelines for their city."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "material": {
                    "type": "string",
                    "description": "Material category",
                    "enum": [
                        "Paper", "Plastic", "Glass", "E-waste",
                        "Metal", "Organic", "Batteries", "Clothing",
                    ],
                },
                "city": {
                    "type": "string",
                    "description": "Indian city name (e.g. Mumbai, Delhi, Bangalore)",
                },
            },
            "required": ["material", "city"],
        },
    },
    {
        "name": "web_search",
        "description": (
            "Search the web for latest eco news, government schemes, local recycling "
            "centers, or any current information. Use when the user asks about recent "
            "events, new policies, or needs up-to-date information not in your training data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "check_scheme",
        "description": (
            "Look up Indian government eco scheme details, eligibility, and benefits. "
            "Use when the user asks about subsidies, government programs, or financial "
            "incentives for eco-friendly actions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "scheme_name": {
                    "type": "string",
                    "description": (
                        "Specific scheme name (e.g. 'PM Surya Ghar', 'FAME II', "
                        "'Swachh Bharat', 'Jal Jeevan Mission', 'UJALA')"
                    ),
                },
                "category": {
                    "type": "string",
                    "description": "Scheme category if name not specified",
                    "enum": ["solar", "EV", "water", "waste", "energy", "agriculture"],
                },
            },
        },
    },
    {
        "name": "analyze_household",
        "description": (
            "Analyze a household profile and suggest a personalized eco action plan "
            "based on location, family size, and current habits. Use when the user "
            "wants a comprehensive plan or personalized recommendations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Indian city name",
                },
                "members": {
                    "type": "integer",
                    "description": "Number of household members",
                },
                "habits": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Current eco habits the household already practices",
                },
            },
            "required": ["location", "members"],
        },
    },
]


# ===========================================================================
#  INDIAN GOVERNMENT ECO SCHEMES DATABASE
#  Static lookup for quick access. Falls back to web search if not found.
# ===========================================================================
SCHEMES_DB: dict[str, dict] = {
    "PM Surya Ghar": {
        "full_name": "PM Surya Ghar Muft Bijli Yojana",
        "category": "solar",
        "description": "Rooftop solar panel installation subsidy for residential homes",
        "benefit": "Up to 300 units of free electricity per month; 40% subsidy on installation cost for systems up to 3 kW",
        "eligibility": "Indian resident with own rooftop; must apply via portal pmsuryaghar.gov.in",
        "how_to_apply": "Register at pmsuryaghar.gov.in → get vendor quote → apply for subsidy → install → inspection → subsidy disbursed",
    },
    "FAME II": {
        "full_name": "Faster Adoption and Manufacturing of Electric Vehicles (FAME II)",
        "category": "EV",
        "description": "Subsidy for electric vehicles, especially 2-wheelers and 3-wheelers",
        "benefit": "Up to Rs 60,000 for electric 2-wheelers; up to Rs 1.5 lakh for electric 3-wheelers; varies by vehicle type",
        "eligibility": "Purchase of notified electric vehicles from registered dealers; vehicle must be registered in India",
        "how_to_apply": "Subsidy applied at point of purchase through registered dealer; no separate application needed",
    },
    "Swachh Bharat Mission": {
        "full_name": "Swachh Bharat Mission (Urban 2.0)",
        "category": "waste",
        "description": "National mission for sanitation and waste management",
        "benefit": "Free waste collection services; community composting support; toilet construction subsidies",
        "eligibility": "All urban households; waste collectors registered with ULB",
        "how_to_apply": "Contact local municipal corporation/ULB for waste collection registration; composting support via ward office",
    },
    "Jal Jeevan Mission": {
        "full_name": "Jal Jeevan Mission",
        "category": "water",
        "description": "Har Ghar Jal — functional tap water connection to every rural household",
        "benefit": "Functional tap water connection; water quality testing; community water supply management",
        "eligibility": "Rural households without functional tap water connection",
        "how_to_apply": "Apply through Gram Panchayat; village water and sanitation committee (VWSC) manages implementation",
    },
    "UJALA": {
        "full_name": "Ujala LED Bulb Distribution Scheme",
        "category": "energy",
        "description": "Subsidized LED bulb distribution across India",
        "benefit": "LED bulbs at Rs 10-15 per bulb (vs Rs 50-80 market price); 9W LED replaces 60W incandescent",
        "eligibility": "All Indian households; exchange old bulbs for LED at distribution centers",
        "how_to_apply": "Visit nearest EESL/Discom distribution center; exchange old incandescent/CFL for LED bulbs",
    },
    "National Biogas Programme": {
        "full_name": "National Biogas and Manure Management Programme (NBMMP)",
        "category": "waste",
        "description": "Subsidy for household biogas plants",
        "benefit": "40-60% capital subsidy on biogas plant installation; varies by category (SC/ST/Others)",
        "eligibility": "Rural households with cattle dung availability; SC/ST families get higher subsidy",
        "how_to_apply": "Apply through District Nodal Agency (DNA) or Block Development Officer (BDO)",
    },
    "PM e-DRIVE": {
        "full_name": "PM Electric Drive Revolution in Innovative Vehicle Enhancement (PM e-DRIVE)",
        "category": "EV",
        "description": "Successor to FAME II; extended EV subsidies and charging infrastructure",
        "benefit": "Demand incentive for EVs; EV charging infrastructure support; extends beyond 2024",
        "eligibility": "Same as FAME II; purchase of notified EVs from registered dealers",
        "how_to_apply": "Subsidy applied at point of purchase through registered dealer",
    },
    "KUSUM": {
        "full_name": "Kisan Urja Suraksha evam Utthaan Mahabhiyan (KUSUM)",
        "category": "solar",
        "description": "Solar pumps and grid-connected solar for farmers",
        "benefit": "60% subsidy on solar water pumps; 30% loan from banks; selling surplus solar power to DISCOM",
        "eligibility": "Farmer with existing grid-connected agriculture pump or need for new pump",
        "how_to_apply": "Apply through state agriculture department or MNRE portal; DISCOM tie-up for grid connectivity",
    },
}


# ===========================================================================
#  TOOL EXECUTOR
# ===========================================================================
def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name with given arguments and return result as string.

    Args:
        name: Tool name matching one of the TOOLS definitions.
        args: Dictionary of arguments matching the tool's parameter schema.

    Returns:
        Tool execution result as a formatted string.

    Raises:
        ValueError: Unknown tool name.
    """
    logger.info("Executing tool: %s with args: %s", name, args)

    if name == "calculate_impact":
        return _execute_calculate_impact(args)
    elif name == "get_recycling_guide":
        return _execute_recycling_guide(args)
    elif name == "web_search":
        return _execute_web_search(args)
    elif name == "check_scheme":
        return _execute_check_scheme(args)
    elif name == "analyze_household":
        return _execute_analyze_household(args)
    else:
        raise ValueError(f"Unknown tool: {name}")


def _execute_calculate_impact(args: dict) -> str:
    """Calculate impact for a single action or list of actions."""
    action_slug = args.get("action_slug", "")
    members = args.get("members", 1)

    # Support comma-separated slugs for multi-action queries
    slugs = [s.strip() for s in action_slug.split(",") if s.strip()]

    if not slugs:
        return "Error: No action slug provided."

    results = []
    for slug in slugs:
        entry = IMPACT_TABLE.get(slug)
        if not entry:
            results.append(f"- {slug}: Unknown action (not in impact table)")
            continue

        scaled_co2 = entry["co2_kg_year"] * members
        scaled_water = entry["water_L_day"] * members
        scaled_waste = entry["waste_kg_year"] * members

        results.append(
            f"- **{entry['label']}** ({slug}):\n"
            f"  CO2: {scaled_co2:.1f} kg/year | "
            f"Water: {scaled_water:.1f} L/day | "
            f"Waste: {scaled_waste:.1f} kg/year\n"
            f"  Source: [{entry['source']}] {entry['note']}"
        )

    header = f"Impact calculation for **{members}** household member(s):\n\n"
    return header + "\n".join(results)


def _execute_recycling_guide(args: dict) -> str:
    """Get recycling guide for a material and city."""
    material = args.get("material", "")
    city = args.get("city", "")

    if not material or not city:
        return "Error: Both material and city are required."

    if city not in INDIAN_CITIES:
        city_list = ", ".join(INDIAN_CITIES[:5]) + f", and {len(INDIAN_CITIES)-5} more"
        return (
            f"City '{city}' not in our database. "
            f"Supported cities: {city_list}. "
            f"Please try one of these cities."
        )

    try:
        guide = get_recycling_guide(material, city)
        return f"## Recycling Guide: {material} in {city}\n\n{guide}"
    except Exception as e:
        return f"Error getting recycling guide: {e}"


def _execute_web_search(args: dict) -> str:
    """Search the web using DuckDuckGo."""
    query = args.get("query", "")
    if not query:
        return "Error: Search query is required."

    try:
        # Try new ddgs package first, fall back to duckduckgo_search
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))

        if not results:
            return f"No results found for: {query}. Try a different search query."

        current_date = datetime.now().strftime("%B %d, %Y")
        formatted = [f"*Search conducted on: {current_date}*\n"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            body = r.get("body", "No description")
            url = r.get("href", "")
            formatted.append(f"{i}. **{title}**\n   {body}\n   {url}")

        return f"## Web Search Results: {query}\n\n" + "\n\n".join(formatted)

    except ImportError:
        return (
            "Web search is not available. "
            "Install ddgs: pip install ddgs"
        )
    except Exception as e:
        return f"Web search failed: {e}. Please try again or use check_scheme for known schemes."


def _execute_check_scheme(args: dict) -> str:
    """Look up Indian government eco scheme details."""
    scheme_name = args.get("scheme_name", "")
    category = args.get("category", "")

    # Direct lookup by name
    if scheme_name:
        # Fuzzy match: try exact, then partial
        scheme = SCHEMES_DB.get(scheme_name)
        if not scheme:
            for key in SCHEMES_DB:
                if scheme_name.lower() in key.lower() or key.lower() in scheme_name.lower():
                    scheme = SCHEMES_DB[key]
                    scheme_name = key
                    break

        if scheme:
            return _format_scheme(scheme_name, scheme)

        return (
            f"Scheme '{scheme_name}' not found in local database. "
            f"Use web_search tool to find current information about this scheme."
        )

    # Lookup by category
    if category:
        matching = [
            (name, s) for name, s in SCHEMES_DB.items()
            if s.get("category") == category
        ]
        if matching:
            formatted = []
            for name, scheme in matching:
                formatted.append(_format_scheme(name, scheme))
            return f"## Government Schemes: {category.title()}\n\n" + "\n\n---\n\n".join(formatted)
        return f"No schemes found for category: {category}. Try web_search for more options."

    # List all schemes
    formatted = []
    for name, scheme in SCHEMES_DB.items():
        formatted.append(f"- **{name}** ({scheme['category']}): {scheme['description']}")
    return "## Available Government Eco Schemes\n\n" + "\n".join(formatted)


def _format_scheme(name: str, scheme: dict) -> str:
    """Format a single scheme for display."""
    return (
        f"### {scheme.get('full_name', name)}\n\n"
        f"**Category:** {scheme['category'].title()}\n\n"
        f"**Description:** {scheme['description']}\n\n"
        f"**Benefits:** {scheme['benefit']}\n\n"
        f"**Eligibility:** {scheme['eligibility']}\n\n"
        f"**How to Apply:** {scheme['how_to_apply']}"
    )


def _execute_analyze_household(args: dict) -> str:
    """Analyze household and suggest personalized action plan using LLM."""
    location = args.get("location", "India")
    members = args.get("members", 1)
    habits = args.get("habits", [])

    # Build a list of actions the household does NOT already do
    all_actions = list(IMPACT_TABLE.keys())
    habit_slugs = set()
    for habit in habits:
        habit_lower = habit.lower()
        for slug, entry in IMPACT_TABLE.items():
            if habit_lower in entry["label"].lower() or slug in habit_lower:
                habit_slugs.add(slug)

    new_actions = [a for a in all_actions if a not in habit_slugs]

    # Use LLM to analyze and recommend
    analysis_prompt = (
        f"Analyze this Indian household and suggest a personalized eco action plan:\n\n"
        f"**Location:** {location}, India\n"
        f"**Household members:** {members}\n"
        f"**Current eco habits:** {', '.join(habits) if habits else 'None specified'}\n\n"
        f"**Available new actions** (not yet practiced):\n"
    )
    for slug in new_actions:
        entry = IMPACT_TABLE.get(slug, {})
        analysis_prompt += (
            f"- {slug}: {entry.get('label', slug)} — "
            f"{entry.get('co2_kg_year', 0) * members:.0f} kg CO2/year, "
            f"{entry.get('water_L_day', 0) * members:.0f} L water/day\n"
        )

    analysis_prompt += (
        f"\nProvide a **prioritized action plan** for this household:\n"
        f"1. Top 3 highest-impact actions they should start with\n"
        f"2. Quick wins (easy, low-cost)\n"
        f"3. Long-term investments (higher cost, higher impact)\n"
        f"4. Location-specific tips for {location}\n"
        f"5. Scale all numbers to {members} person(s)\n"
        f"\nBe specific, practical, and India-focused."
    )

    try:
        model = _get_model()
        response = model.chat(
            messages=[
                {"role": "system", "content": AGENT_INSTRUCTIONS.strip()},
                {"role": "user", "content": analysis_prompt},
            ],
            params={"max_tokens": 800, "temperature": 0.6},
        )
        analysis = response["choices"][0]["message"]["content"].strip()

        # Prepend summary
        impact = compute_session_impact(new_actions[:5], members)
        summary = (
            f"## Household Analysis: {members}-person household in {location}\n\n"
            f"**Current habits:** {', '.join(habits) if habits else 'None'}\n\n"
            f"**Potential impact** (top 5 new actions): "
            f"{impact['co2_kg_year']:.0f} kg CO2/year, "
            f"{impact['water_L_day']:.0f} L water/day\n\n"
            f"---\n\n"
        )
        return summary + analysis

    except Exception as e:
        return f"Error analyzing household: {e}. Falling back to basic recommendations."
