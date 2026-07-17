# 🌌 ACME Multi-Agent Workspace

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://react.dev)
[![Google Cloud](https://img.shields.io/badge/Google_Cloud-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white)](https://cloud.google.com)
[![Gemini](https://img.shields.io/badge/Gemini-8E75C2?style=for-the-badge&logo=google-gemini&logoColor=white)](https://deepmind.google/technologies/gemini)

A production-grade, modular multi-agent ecosystem engineered for **ACME Media**. This system orchestrates automated marketing campaign design and interactive customer support workflows using Vertex AI and the Gemini model suite.

---

## 🗺️ System Interaction Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as Brand Manager / Customer
    participant FE as React Frontend
    participant MA as Marketing Agent (FastAPI)
    participant CA as Customer Agent (FastAPI)
    participant BQ as BigQuery Database
    participant GT as Google Trends (Public Data)

    Note over User, FE: Campaign Generation
    User->>FE: Ask for campaign (e.g., Japan trends)
    FE->>MA: POST /query (Run workflow)
    MA->>GT: Query Trends (auto-redirect country swap)
    MA->>BQ: Fetch Episode views & metadata
    MA->>MA: Critic review & revision loop
    MA-->>FE: Stream campaign proposal (with charts)
    FE-->>User: Render Glassmorphic UI Dashboard

    Note over User, CA: Customer Support
    User->>FE: Chat bubble: "I'm bored"
    FE->>CA: POST /chat (ReAct loop)
    CA->>BQ: Query top sentiment episodes
    BQ-->>CA: Return scores (e.g. 0.92)
    CA-->>FE: Suggest 2-3 friendly options
```

---

## 📦 Monorepo Component Overview

| Component | Stack | Primary Responsibilities | Core Logic |
| :--- | :--- | :--- | :--- |
| **[Marketing Agent](file:///usr/local/google/home/owq/Desktop/Agents%20for%20ACME/marketing-agent/README.md)** | `Python`, `FastAPI`, `ADK 2.0` | Workflow orchestration, BQ integration, geographic trend swapping | `agent.py` |
| **[Customer Agent](file:///usr/local/google/home/owq/Desktop/Agents%20for%20ACME/customer-agent/README.md)** | `Python`, `FastAPI`, `ADK ReAct` | Answering queries, sentiment-driven recommendations, rate-limiting | `agent.py` |
| **[Frontend Dashboard](file:///usr/local/google/home/owq/Desktop/Agents%20for%20ACME/frontend/README.md)** | `React`, `Vite`, `Vega-Lite` | Interactive metrics rendering, step-by-step progress tracking, support chat widget | `App.jsx` |

---

## ⚡ Key Highlights & Defensibility

> [!NOTE]
> ### 🛡️ Multi-Region Resiliency Fallback
> The system implements a robust, thread-safe fallback chain that rotates requests across regional endpoints (`us-east4`, `us-west1`, `europe-west4`) with exponential backoff on HTTP `429 RESOURCE_EXHAUSTED` responses.

> [!TIP]
> ### 📊 Smart Trends Query Routing
> Google Trends queries are dynamically routed. If a query matches a known country (e.g., `"Japan"`), the query is swapped into a regional filter to pull top trending topics rather than searching for the string "Japan" literally, eliminating search-term bias.

---

## 🚀 Getting Started

Ready to deploy or run locally? Read the detailed, step-by-step instructions in the:
👉 **[Deployment & Usage Guide](file:///usr/local/google/home/owq/Desktop/Agents%20for%20ACME/DEPLOYMENT_GUIDE.md)**
