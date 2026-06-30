# Customer Agent

A friendly, direct assistant for chatting with ACME customers, answering questions, and recommending media assets/podcasts.

## Project Structure

```
customer-agent/
├── customer_app/         # Core Agent Code
│   ├── agent.py          # Main entrypoint and agent definitions
│   ├── plugins.py        # Throttling plugin for rate limiting
│   ├── tools.py          # BigQuery media database query tools
│   └── app_utils/        # ADK internal system configurations
└── pyproject.toml        # Poetry / UV Python dependencies
```

## Features

- **Interactive ReAct Loop:** Seamlessly queries BigQuery and Google Trends based on conversation context.
- **Sentiment-Driven Suggestions:** Recommends highly-rated podcast episodes when the user indicates they are bored.
- **Brief & Conversational:** Avoids wall-of-text responses by enforcing maximum token lengths.

## Development & Test Commands

Start the agent server locally:
```bash
uv run fastapi dev customer_app/fast_api_app.py
```
