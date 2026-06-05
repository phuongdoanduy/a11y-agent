# ADK Examples — MCP + Graph + Multi-Agent

This directory contains examples demonstrating advanced Google ADK (Agent Development Kit) features.

## `mcp_graph_multiagent_demo.py`

Demonstrates all three major ADK features working together:

### 1. MCP (Model Context Protocol)
Connect to external tool servers for filesystem, GitHub, database, and more.

```python
from google.adk.tools.mcp_tool import McpToolset

filesystem_mcp = McpToolset(
    server_params={
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-e", "/path/to/project"],
    },
    tool_filter=["read_file", "list_directory"],
)
```

### 2. Graph Workflow (ADK 2.0)
DAG-based agent orchestration with parallel branches and conditional routing.

```python
from google.adk.workflow import Workflow, START

workflow = Workflow(
    name="my_workflow",
    edges=[
        (START, planner, reporter),          # Chain: START → planner → reporter
        (planner, scanner_1),                # Parallel: planner → scanner_1
        (planner, scanner_2),                # Parallel: planner → scanner_2
        (scanner_1, reporter),               # Merge: scanner_1 → reporter
        (scanner_2, reporter),               # Merge: scanner_2 → reporter
    ],
    max_concurrency=3,
)
```

### 3. Multi-Agent
Multiple specialized agents collaborating through session state.

```python
from google.adk.agents import LlmAgent

planner = LlmAgent(name="planner", output_key="plan")
scanner = LlmAgent(name="scanner", output_key="results")
reporter = LlmAgent(name="reporter")  # Reads {plan} and {results}
```

## Architecture

```
         ┌─────────┐
         │  START   │
         └────┬─────┘
              ▼
        ┌──────────┐
        │ planner   │  Creates audit plan
        └────┬─────┘
         ┌───┴───┐
         ▼       ▼
   ┌────────┐ ┌────────┐
   │scan_ios│ │scan_web│  Parallel scanning
   └───┬────┘ └───┬────┘
       └─────┬────┘
             ▼
       ┌──────────┐
       │ reporter  │  Merges results
       └────┬─────┘
            ▼
       ┌─────────┐
       │   END   │
       └─────────┘
```

## Running

```bash
# From project root
source .venv/bin/activate
python -m app.examples.mcp_graph_multiagent_demo
```

## Prerequisites

```bash
# ADK 2.0+ required for Workflow API
pip install "google-adk>=2.0.0"

# MCP package required for McpToolset
pip install mcp

# Or with uv
uv add "google-adk>=2.0.0" mcp
```

## Key ADK Concepts

| Concept | What it does | Example |
|---------|-------------|---------|
| `output_key` | Agent writes output to session state key | `output_key="plan"` |
| `edges` | Define execution order in workflow graph | `(START, agent_a, agent_b)` |
| `McpToolset` | Connect to MCP server for external tools | `McpToolset(server_params={...})` |
| `FunctionNode` | Python function as a workflow node | `FunctionNode(func=my_func)` |
| `max_concurrency` | Limit parallel agent execution | `max_concurrency=3` |
| `BuiltInPlanner` | Enable extended thinking on agents | `planner=BuiltInPlanner(...)` |

## References

- [ADK Documentation](https://adk.dev/)
- [ADK 2.0 Workflow API](https://adk.dev/agents/workflows/index.md)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [ADK Samples](https://github.com/google/adk-samples)
