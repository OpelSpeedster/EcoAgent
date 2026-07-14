"""
agent.py
--------
Agentic loop for EcoAgent.

Provides:
  - agent_loop()  : Multi-step reasoning with tool use
  - format_tool_calls() : Format tool call log for UI display
"""

import os
import json
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
    AGENT_INSTRUCTIONS,
    _build_system_prompt,
    _get_model,
)
from tools import TOOLS, execute_tool

logger = logging.getLogger(__name__)

# Safety limit to prevent infinite loops
MAX_ITERATIONS = 5

# Maximum tool calls before forced synthesis
MAX_TOOL_CALLS_BEFORE_SYNTHESIS = 2

# System prompt for agent mode — extends base instructions with tool usage
AGENT_SYSTEM_PROMPT = AGENT_INSTRUCTIONS.strip() + """

## Tool Usage (Agent Mode)

You have access to tools that provide real-time data and calculations.
ALWAYS use tools when they can provide accurate data — never make up numbers.

### When to Use Each Tool:
1. **calculate_impact** — User asks about CO2/water/waste savings, impact numbers, or compares actions
2. **get_recycling_guide** — User asks how to recycle, where to dispose, recycling instructions
3. **web_search** — User asks about LATEST news, new schemes, recent events, current information, local services, any time-sensitive query
4. **check_scheme** — User asks about government subsidies, eligibility, scheme details
5. **analyze_household** — User wants a personalized action plan based on their profile

### CRITICAL RULES:
- TODAY'S DATE: """ + datetime.now().strftime("%B %d, %Y") + """ — use this as the current date
- For ANY question about "latest", "new", "recent", "current", "2024", "2025", "2026" — you MUST use web_search
- For ANY question about government schemes — use check_scheme first, then web_search if user wants latest updates
- Do NOT rely on your training data for time-sensitive information
- CRITICAL: Use the ACTUAL search results provided, not your training data — the search results contain current information
- Never say "As of today (August 2025)" or similar — the current date is stated above
- You may call 1-2 tools in sequence before giving your final answer
- DO NOT call more than 2 tools — after getting results, IMMEDIATELY provide your final answer
- Once you have tool results, SYNTHESIZE them into a helpful answer — do NOT call more tools
"""


def agent_loop(
    user_message: str,
    profile: dict | None = None,
    history: list[dict] | None = None,
) -> tuple[str, list[str]]:
    """Agentic loop: reason -> act -> observe -> repeat until final answer.

    Uses IBM Granite's native function calling capability. The model decides
    which tools to call based on the user's query.

    Args:
        user_message: The user's current message.
        profile:      Optional household profile dict.
        history:      Optional conversation history (list of role/content dicts).

    Returns:
        Tuple of (final_answer, tool_calls_log) where tool_calls_log
        is a list of tool names that were invoked.

    Raises:
        RuntimeError: If the agent exceeds MAX_ITERATIONS without a final answer.
    """
    model = _get_model()
    tool_calls_log: list[str] = []

    # Build system prompt with profile context
    system_prompt = AGENT_SYSTEM_PROMPT
    if profile:
        profile_block = _build_profile_block(profile)
        system_prompt += profile_block

    # Build initial messages
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt}
    ]

    # Add conversation history (if any)
    if history:
        for turn in history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            # Extract text from content blocks if needed
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                content = " ".join(text_parts)
            if content:
                messages.append({"role": role, "content": content})

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    # Tool definitions for the API call (OpenAI-compatible format)
    tool_defs = _format_tools_for_api()

    logger.info("Agent loop starting for query: %s", user_message[:100])

    # Agentic loop
    for iteration in range(MAX_ITERATIONS):
        logger.info("Agent iteration %d/%d (tools called so far: %d)", 
                    iteration + 1, MAX_ITERATIONS, len(tool_calls_log))

        # After MAX_TOOL_CALLS_BEFORE_SYNTHESIS tool calls, force synthesis
        if len(tool_calls_log) >= MAX_TOOL_CALLS_BEFORE_SYNTHESIS:
            logger.info("Forcing synthesis after %d tool calls", len(tool_calls_log))
            messages.append({
                "role": "user",
                "content": (
                    "[SYSTEM] You have enough information now. "
                    "Do NOT call any more tools. "
                    "Synthesize all the tool results above into a clear, helpful answer. "
                    "Provide your final response to the user now."
                )
            })

        try:
            # Determine whether to allow tool calls
            # After MAX_TOOL_CALLS_BEFORE_SYNTHESIS, force text-only response
            if len(tool_calls_log) >= MAX_TOOL_CALLS_BEFORE_SYNTHESIS:
                # Force text response — no more tools
                response = model.chat(
                    messages=messages,
                    params={
                        "max_tokens": 1500,
                        "temperature": 0.5,
                        "top_p": 0.95,
                    },
                )
            else:
                # Allow tool calls
                response = model.chat(
                    messages=messages,
                    tools=tool_defs,
                    tool_choice_option="auto",
                    params={
                        "max_tokens": 1500,
                        "temperature": 0.5,
                        "top_p": 0.95,
                    },
                )
        except Exception as e:
            logger.error("LLM call failed in agent loop: %s", e)
            raise RuntimeError(f"Agent loop LLM call failed: {e}") from e

        # Parse the response
        choice = response["choices"][0]
        message = choice["message"]
        assistant_content = message.get("content", "") or ""
        tool_calls = message.get("tool_calls", [])

        logger.info("Response content length: %d chars, tool calls: %d", 
                    len(assistant_content), len(tool_calls))

        # If no tool calls, this is the final answer
        if not tool_calls:
            logger.info("Agent loop completed at iteration %d (final answer)", iteration + 1)
            return assistant_content.strip(), tool_calls_log

        # Process each tool call
        for tool_call in tool_calls:
            func = tool_call.get("function", {})
            tool_name = func.get("name", "")
            tool_args_str = func.get("arguments", "{}")

            # Parse arguments — API returns double-encoded JSON string
            try:
                tool_args = json.loads(tool_args_str)
                # If result is still a string, parse again (double-encoded)
                if isinstance(tool_args, str):
                    tool_args = json.loads(tool_args)
            except json.JSONDecodeError:
                logger.error("Failed to parse tool args: %s", tool_args_str)
                tool_args = {}

            logger.info("Executing tool: %s(%s)", tool_name, tool_args)
            tool_calls_log.append(tool_name)

            # Execute the tool
            try:
                tool_result = execute_tool(tool_name, tool_args)
            except Exception as e:
                logger.error("Tool execution failed: %s", e)
                tool_result = f"Error executing {tool_name}: {e}"

            logger.info("Tool result length: %d chars", len(tool_result))

            # Add the assistant message with tool calls to history
            messages.append({
                "role": "assistant",
                "content": assistant_content if assistant_content else None,
                "tool_calls": [{
                    "id": tool_call.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": tool_args_str,
                    }
                }],
            })

            # Add the tool result to history
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.get("id", ""),
                "content": tool_result,
            })

    # Safety: max iterations reached — synthesize what we have
    logger.warning("Agent loop hit MAX_ITERATIONS (%d), synthesizing final answer", MAX_ITERATIONS)
    
    # Make one final call without tools to get a synthesized answer
    try:
        response = model.chat(
            messages=messages + [{
                "role": "user",
                "content": (
                    "[SYSTEM] You must provide your final answer now. "
                    "Synthesize all the tool results above into a clear, helpful response. "
                    "Do NOT call any more tools."
                )
            }],
            params={
                "max_tokens": 1500,
                "temperature": 0.5,
                "top_p": 0.95,
            },
        )
        final_content = response["choices"][0]["message"].get("content", "")
        if final_content and len(final_content.strip()) > 50:
            return final_content.strip(), tool_calls_log
    except Exception as e:
        logger.error("Final synthesis call failed: %s", e)

    # If all else fails, return a helpful message
    return (
        "Based on the information gathered, please refer to the tool results above "
        "for details. Let me know if you'd like me to elaborate on any specific point.",
        tool_calls_log,
    )


def _build_profile_block(profile: dict) -> str:
    """Build profile context block for the system prompt."""
    if not profile:
        return ""

    members = profile.get("members", 1)
    location = profile.get("location", "India")
    habits = profile.get("habits", [])
    name = profile.get("name", "")

    return (
        f"\n\n## Current Household Profile\n"
        f"- Household name: {name or 'Not provided'}\n"
        f"- Location: {location}\n"
        f"- Members: {members}\n"
        f"- Current eco habits: {', '.join(habits) if habits else 'None specified'}\n"
        f"\nScale all impact estimates to {members} person(s) where relevant. "
        f"Do not re-recommend habits the household already practises."
    )


def _format_tools_for_api() -> list[dict]:
    """Format tool definitions for the IBM Granite API (OpenAI-compatible)."""
    formatted = []
    for tool in TOOLS:
        formatted.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            },
        })
    return formatted


def format_tool_calls(tool_calls: list[str]) -> str:
    """Format a list of tool call names for display in the UI.

    Args:
        tool_calls: List of tool names that were invoked.

    Returns:
        Markdown string showing tool usage.
    """
    if not tool_calls:
        return ""

    tool_labels = {
        "calculate_impact": "🧮 Impact Calculator",
        "get_recycling_guide": "♻️ Recycling Guide",
        "web_search": "🔍 Web Search",
        "check_scheme": "🏛️ Scheme Checker",
        "analyze_household": "👥 Household Profiler",
    }

    lines = ["**🔧 Tools used:**"]
    for i, tool in enumerate(tool_calls, 1):
        label = tool_labels.get(tool, tool)
        lines.append(f"{i}. {label}")

    return "\n".join(lines)
