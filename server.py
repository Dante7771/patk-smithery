#!/usr/bin/env python3
"""
PATK — PFC Agent Token Killer (Smithery Edition)
=================================================

HTTP MCP Server for Smithery Gateway.
Filters terminal output to reduce token usage by 40-80%.

Filter runs embedded — no external API, no DB, no credits.
Smithery handles auth and billing on their end.

TOOLS:
  patk_filter_output → Filter captured terminal output (primary tool)
  patk_status        → Show service info and session stats
"""

import os
from mcp.server.fastmcp import FastMCP
from filter import filter_pipeline

# ── MCP Server ─────────────────────────────────────────────────────────────────
mcp = FastMCP("patk")

# Session statistics (per instance)
_session_calls: int = 0
_session_chars_saved: int = 0


# ── Tools ───────────────────────────────────────────────────────────────────────
@mcp.tool(
    name="patk_filter_output",
    annotations={
        "title": "Filter Terminal Output",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def patk_filter_output(text: str, max_lines: int = 50) -> str:
    """Filter and compress terminal output to reduce Claude's context usage.

    Reduces terminal output by 40-80% by removing noise:
    - ANSI color codes
    - Progress bars and download indicators
    - Repeated/duplicate lines (condensed to summary)
    - Low-entropy filler lines
    - Keeps: errors, warnings, success messages, important output

    WHEN TO USE:
    - npm install / yarn / pip install / cargo build output
    - pytest / jest / cargo test results
    - docker build logs
    - Any terminal output > 15 lines before passing to Claude

    WORKFLOW:
    1. Run your command via Bash tool → capture raw output
    2. Pass raw output to this tool
    3. Use the filtered result — Claude sees only what matters

    Args:
        text: Raw terminal output to filter (max 200KB per call)
        max_lines: Maximum output lines to keep (1-500, default 50)

    Returns:
        Filtered output with reduction statistics.
    """
    global _session_calls, _session_chars_saved

    if not text or not text.strip():
        return "❌ Empty input — nothing to filter."

    if len(text) > 200_000:
        return (
            "❌ Input too large (max 200KB per call). "
            "Split into smaller chunks."
        )

    result = filter_pipeline(text, max_lines=max_lines)

    _session_calls += 1
    chars_saved = result["original_chars"] - result["filtered_chars"]
    _session_chars_saved += chars_saved

    tokens_saved = chars_saved // 4
    dollar_saved = tokens_saved * 0.000003
    session_tokens = _session_chars_saved // 4

    return (
        f"{result['filtered_text']}\n"
        f"---\n"
        f"⚡ PATK Smithery  |  {result['reduction_pct']}% Reduktion  |  "
        f"{result['original_lines']} → {result['filtered_lines']} Zeilen  |  "
        f"~{tokens_saved:,} Tokens gespart ≈ ${dollar_saved:.4f}\n"
        f"📊 Session: {_session_calls} Calls, ~{session_tokens:,} Tokens gespart gesamt"
    )


@mcp.tool(
    name="patk_status",
    annotations={
        "title": "PATK Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def patk_status() -> str:
    """Show PATK service status and session statistics.

    Returns:
        Status report with filter info and session stats.
    """
    session_tokens = _session_chars_saved // 4
    dollar_saved = session_tokens * 0.000003

    return (
        f"# PFC Agent Token Killer — Smithery Edition\n\n"
        f"**Mode:** 🌐 Smithery Cloud (embedded filter, no API key needed)\n"
        f"**Session calls:** {_session_calls}\n"
        f"**Tokens saved this session:** ~{session_tokens:,} ≈ ${dollar_saved:.4f}\n\n"
        f"## Available Tools\n"
        f"- `patk_filter_output` — Filter terminal output (primary tool)\n"
        f"- `patk_status` — This status report\n\n"
        f"## How to Use\n"
        f"1. Run your command via Bash tool\n"
        f"2. Pass the raw output to `patk_filter_output`\n"
        f"3. Claude sees the filtered result — 40-80% less noise\n\n"
        f"## Filter Pipeline\n"
        f"1. ANSI code removal\n"
        f"2. Progress bar detection\n"
        f"3. Pattern condensation (npm warn, pip collect, pytest PASSED...)\n"
        f"4. Duplicate compression\n"
        f"5. Timestamp cluster compression\n"
        f"6. Entropy scoring — keeps errors, warnings, key output"
    )


# ── Entry Point ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    # FastMCP.run() doesn't accept host/port kwargs — use uvicorn directly
    app = mcp.streamable_http_app()
    uvicorn.run(app, host="0.0.0.0", port=port)
