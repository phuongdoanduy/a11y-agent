# Copyright 2026 Optimus Team
# MIT License
#
# Demo: MCP + Graph Workflow + Multi-Agent with Google ADK 2.x
# This example demonstrates all three major ADK features working together:
#   1. MCP (Model Context Protocol) — connect to external tool servers
#   2. Graph Workflow — DAG-based agent orchestration with edges
#   3. Multi-Agent — multiple specialized agents collaborating
#
# Architecture:
#
#   ┌─────────────┐
#   │   START      │
#   └──────┬───────┘
#          ▼
#   ┌─────────────┐
#   │  planner     │  LlmAgent — analyzes input, creates audit plan
#   └──────┬───────┘
#          ▼
#   ┌──────┴──────┐
#   ▼             ▼
# ┌──────┐   ┌──────┐
# │scan_1│   │scan_2│  LlmAgent — parallel scanners (iOS + Web)
# └──┬───┘   └──┬───┘
#    └─────┬────┘
#          ▼
#   ┌─────────────┐
#   │  reporter    │  LlmAgent — merges results, generates report
#   └──────┬───────┘
#          ▼
#   ┌─────────────┐
#   │    END       │
#   └─────────────┘
#
# Run:
#   cd /path/to/epost-a11y-agent
#   source .venv/bin/activate
#   python -m app.examples.mcp_graph_multiagent_demo
#
# Prerequisites:
#   pip install google-adk>=2.0.0 mcp   # MCP package required for McpToolset

from __future__ import annotations

import asyncio
import logging
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.apps.app import App
from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.workflow import START, FunctionNode, Workflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 1. MCP TOOLSET — Connect to external MCP servers
# ═══════════════════════════════════════════════════════════════
# MCP (Model Context Protocol) lets agents use tools from external servers.
# Here we connect to a filesystem MCP server for reading project files.
#
# You can also connect to any MCP server:
#   - GitHub MCP server (repo operations)
#   - Database MCP server (query data)
#   - Custom MCP server (your own tools)
#
# To run a local filesystem MCP server:
#   npx -y @modelcontextprotocol/server-e /path/to/project

# Filesystem MCP — reads files from a target directory
# Uncomment and configure the server_command to use:
#
# filesystem_mcp = McpToolset(
#     server_params={
#         "command": "npx",
#         "args": ["-y", "@modelcontextprotocol/server-e", "/path/to/project"],
#     },
#     tool_filter=["read_file", "list_directory", "search_files"],
# )

# For demo purposes, we define equivalent local tools
# (so the demo runs without an MCP server running)


def read_project_file(file_path: str) -> str:
    """Read a file from the target project directory.

    Args:
        file_path: Relative path to the file within the project.

    Returns:
        File content as string.
    """
    from pathlib import Path

    try:
        full_path = Path(file_path)
        if not full_path.exists():
            return f"Error: File not found: {file_path}"
        return full_path.read_text()[:5000]  # Cap at 5k chars
    except Exception as e:
        return f"Error reading {file_path}: {e}"


def list_project_files(glob_pattern: str = "**/*") -> str:
    """List files in the project matching a glob pattern.

    Args:
        glob_pattern: Glob pattern (e.g. "**/*.swift", "**/*.py")

    Returns:
        JSON list of matching file paths.
    """
    import json
    from pathlib import Path

    try:
        files = [str(p) for p in Path(".").glob(glob_pattern) if p.is_file()]
        return json.dumps({"files": files[:50], "count": len(files)})
    except Exception as e:
        return json.dumps({"error": str(e), "files": [], "count": 0})


# Wrap as ADK FunctionTools
file_reader = FunctionTool(read_project_file)
file_lister = FunctionTool(list_project_files)


# ═══════════════════════════════════════════════════════════════
# 2. MULTI-AGENT — Specialized agents for each task
# ═══════════════════════════════════════════════════════════════

# ── Agent 1: Planner ──────────────────────────────────────────
# Analyzes the input and creates a structured audit plan
planner_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="planner",
    description="Analyzes the audit request and creates a structured plan.",
    instruction="""You are an accessibility audit planner.

Given the user's request, create a structured audit plan with:
1. Target platform (ios/android/web)
2. Files to scan (glob patterns)
3. WCAG criteria to check
4. Priority areas

Output a JSON plan that the scanner agents can use.
Keep it concise and actionable.

User request: {user_request}
""",
    output_key="audit_plan",  # Write plan to session state
)


# ── Agent 2: iOS Scanner ──────────────────────────────────────
# Scans for iOS-specific accessibility patterns
ios_scanner_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="ios_scanner",
    description="Scans codebase for iOS accessibility violations (VoiceOver, UIKit, SwiftUI).",
    instruction="""You are an iOS accessibility scanner.

Read the audit plan from 'audit_plan' state key, then:
1. Use list_project_files to find Swift/SwiftUI files
2. Use read_project_file to examine each file
3. Check for these iOS a11y patterns:
   - Missing accessibilityLabel on interactive elements
   - Missing accessibilityTraits
   - isAccessibilityElement not set
   - Missing .header trait for headings
   - Images without accessibility labels
   - Small touch targets (< 44x44 points)

Output a JSON list of violations found.
""",
    tools=[file_reader, file_lister],
    output_key="ios_scan_result",
)


# ── Agent 3: Web Scanner ──────────────────────────────────────
# Scans for web-specific accessibility patterns
web_scanner_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="web_scanner",
    description="Scans codebase for web accessibility violations (ARIA, keyboard, contrast).",
    instruction="""You are a web accessibility scanner.

Read the audit plan from 'audit_plan' state key, then:
1. Use list_project_files to find HTML/JSX/TSX files
2. Use read_project_file to examine each file
3. Check for these web a11y patterns:
   - Images without alt attributes
   - Buttons/links without accessible names
   - Missing ARIA labels on interactive elements
   - tabIndex > 0 (anti-pattern)
   - Missing form labels
   - Color contrast issues in CSS
   - Missing heading hierarchy

Output a JSON list of violations found.
""",
    tools=[file_reader, file_lister],
    output_key="web_scan_result",
)


# ── Agent 4: Reporter ─────────────────────────────────────────
# Merges results from all scanners into a final report
reporter_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="reporter",
    description="Merges scan results into a comprehensive accessibility report.",
    instruction="""You are an accessibility report composer.

Merge the scan results from all scanner agents:
- iOS results: {ios_scan_result}
- Web results: {web_scan_result}

Create a comprehensive report with:
1. Executive Summary (total violations, score)
2. Violations by severity (critical → minor)
3. File-by-file breakdown
4. Remediation priorities
5. WCAG coverage matrix

Format as markdown.
""",
    output_key="final_report",
)


# ═══════════════════════════════════════════════════════════════
# 3. GRAPH WORKFLOW — DAG-based orchestration
# ═══════════════════════════════════════════════════════════════
# ADK 2.0 Workflow API lets you define agent execution as a graph:
#   - Edges define execution order
#   - Parallel branches run concurrently
#   - Data flows through session state (output_key → input)
#
# Graph structure:
#   START → planner → [ios_scanner, web_scanner] → reporter → END
#
# The tuple syntax (a, b, c) creates a chain: a → b → c
# Multiple edges from the same node create parallel branches.

a11y_workflow = Workflow(
    name="a11y_mcp_graph_demo",
    description="MCP + Graph + Multi-Agent accessibility audit workflow",
    edges=[
        # Chain: START → planner → reporter → END
        (START, planner_agent, reporter_agent),
        # Parallel branch: planner → ios_scanner
        (planner_agent, ios_scanner_agent),
        # Parallel branch: planner → web_scanner
        (planner_agent, web_scanner_agent),
        # Merge: both scanners feed into reporter
        (ios_scanner_agent, reporter_agent),
        (web_scanner_agent, reporter_agent),
    ],
    max_concurrency=3,  # Max 3 agents running in parallel
)


# ═══════════════════════════════════════════════════════════════
# 4. FUNCTION NODE — Custom logic in the graph
# ═══════════════════════════════════════════════════════════════
# You can also add Python functions as nodes in the workflow graph.
# FunctionNode reads/writes session state directly.


def compute_final_score(state: dict[str, Any]) -> dict[str, Any]:
    """Compute final accessibility score from all scan results.

    This FunctionNode runs as a step in the workflow graph,
    reading from and writing to session state.
    """
    ios_result = state.get("ios_scan_result", {})
    web_result = state.get("web_scan_result", {})

    # Parse results (simplified)
    ios_violations = ios_result.get("violations", []) if isinstance(ios_result, dict) else []
    web_violations = web_result.get("violations", []) if isinstance(web_result, dict) else []

    total = len(ios_violations) + len(web_violations)
    score = max(0, 100 - (total * 5))

    return {
        "total_violations": total,
        "score": score,
        "pass": score >= 85,
    }


# Example: Workflow with FunctionNode
# Uncomment to use:
#
# score_node = FunctionNode(
#     name="score_calculator",
#     func=compute_final_score,
# )
#
# a11y_workflow_with_score = Workflow(
#     name="a11y_with_scoring",
#     edges=[
#         (START, planner_agent),
#         (planner_agent, ios_scanner_agent),
#         (planner_agent, web_scanner_agent),
#         (ios_scanner_agent, score_node),  # FunctionNode after scanners
#         (web_scanner_agent, score_node),
#         (score_node, reporter_agent),
#         (reporter_agent,),
#     ],
# )


# ═══════════════════════════════════════════════════════════════
# 5. APP — Wire it all together
# ═══════════════════════════════════════════════════════════════

# Option A: Use the workflow as root agent (graph-based)
app = App(root_agent=a11y_workflow, name="mcp_graph_demo")

# Option B: Use a single LlmAgent that delegates to sub-agents
# (traditional ADK pattern, no graph)
#
# root_agent = LlmAgent(
#     name="a11y_coordinator",
#     model="gemini-2.0-flash",
#     instruction="You are an a11y audit coordinator...",
#     sub_agents=[planner_agent, ios_scanner_agent, web_scanner_agent, reporter_agent],
# )
# app = App(root_agent=root_agent, name="multiagent_demo")


# ═══════════════════════════════════════════════════════════════
# 6. RUN — Execute the workflow
# ═══════════════════════════════════════════════════════════════

async def main():
    """Run the workflow demo."""
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    runner = InMemoryRunner(app=app)

    # Create a session
    session = await runner.session_service.create_session(
        app_name="mcp_graph_demo",
        user_id="demo_user",
    )

    # Run the workflow
    user_message = types.Content(
        role="user",
        parts=[types.Part(text="Audit this project for accessibility issues. Focus on iOS Swift files and web React files.")],
    )

    print("\n" + "=" * 60)
    print("  MCP + Graph + Multi-Agent Demo")
    print("=" * 60)

    async for event in runner.run_async(
        user_id="demo_user",
        session_id=session.id,
        new_message=user_message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"\n[{event.author}] {part.text[:500]}")

    print("\n" + "=" * 60)
    print("  Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
