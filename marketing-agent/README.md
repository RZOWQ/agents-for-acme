# Marketing Agent

A structured, modular ADK 2.0 marketing campaign generator agent built on Vertex AI and Gemini.

## Project Structure

```
marketing-agent/
├── app/                  # Core Agent Code
│   ├── agent.py          # Main entrypoint and workflow definition
│   ├── agents.py         # Subagent definitions (planner, SQL, generator, critic, refiner)
│   ├── schemas.py        # Pydantic structured output models
│   ├── model_utils.py    # Fallback chains for Multi-Region Vertex AI
│   ├── nodes.py          # Workflow function nodes
│   ├── plugins.py        # ADK plugins (Caching and Throttling)
│   ├── tools.py          # Google Trends & BigQuery connectors
│   └── app_utils/        # ADK internal system configurations
├── tests/                # Unit and integration test suites
├── GEMINI.md             # AI developer guidance
└── pyproject.toml        # Poetry / UV Python dependencies
```

## Features

- **Multi-Region Fallback Chain:** Automatically handles API rate limits (HTTP 429) by transparently falling back between multiple Vertex regional endpoints.
- **Bi-directional Google Trends Search:** Automatically detects query targets and searches regional top trends without hardcoded keyword bias.
- **Workflow State Management:** State fields are explicitly decoupled to prevent variable leakage between iterations.
- **Throttling & Caching Plugins:** Built-in rate limiting and query caches to minimize overhead.

## Development & Test Commands

Run unit and integration tests:
```bash
uv run pytest tests/unit tests/integration
```

Start the agent server locally:
```bash
uv run fastapi dev app/fast_api_app.py
```
