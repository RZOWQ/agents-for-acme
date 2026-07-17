# ACME Agents Workspace

A premium, fully modular multi-agent platform designed for ACME Media, combining real-time marketing campaign automation and customer support service widgets.

---

## 🏗️ Architecture & Component Overview

The repository is structured as a monorepo containing three core components:

```
Agents for ACME/
├── DEPLOYMENT_GUIDE.md     # Setup, local run commands, and Cloud Run deployments
├── marketing-agent/        # Core agent orchestrating campaign analysis
│   └── app/                # Modular workflow nodes, tool connections, schemas
├── customer-agent/         # Customer support assistant responding to client chats
│   └── customer_app/       # Database-connected ReAct support loop
└── frontend/               # Premium React + Vite Glassmorphic Dashboard
    └── src/                # Chart embeds, support chat bubbles, and progress states
```

### 1. [Marketing Agent](file:///usr/local/google/home/owq/Desktop/Agents%20for%20ACME/marketing-agent/README.md)
* **Goal:** Generate strategic marketing campaign documents based on concurrent inputs from internal viewership databases and external Google Trends search analytics.
* **Key Mechanisms:**
  * **Structured Workflows:** Directed Acyclic Graphs (DAG) routing via ADK 2.0.
  * **Multi-Region Fallback:** Transparently reroutes requests between regional Vertex AI endpoints on rate exhaustion (`429 RESOURCE_EXHAUSTED`).
  * **Smart Country Routing:** Automatically swaps country search terms (like `"Japan"`) into strict location filters to retrieve regional trending records directly.

### 2. [Customer Agent](file:///usr/local/google/home/owq/Desktop/Agents%20for%20ACME/customer-agent/README.md)
* **Goal:** Direct assistant that chats with customers, answers media/podcast library questions, and provides tailored, sentiment-based podcast recommendations.
* **Key Mechanisms:** ReAct looping with tool access to BigQuery and Google Trends.

### 3. [Frontend Dashboard](file:///usr/local/google/home/owq/Desktop/Agents%20for%20ACME/frontend/README.md)
* **Goal:** A premium, dark-themed, glassmorphic layout interface enabling workspace collaboration.
* **Key Mechanisms:**
  * **Live Vega-Lite Rendering:** Renders dynamically generated trend lines, allocation donuts, and episode metrics inline.
  * **Workflow Stage Progress:** Displays real-time visual progress mapped to backend agent execution states.
  * **Embedded Chat Widget:** Bridges clients directly to the customer support service.

---

## 🚀 Getting Started

To get started, follow the comprehensive setup, configuration, and launch instructions in the [Deployment & Usage Guide](file:///usr/local/google/home/owq/Desktop/Agents%20for%20ACME/DEPLOYMENT_GUIDE.md).
