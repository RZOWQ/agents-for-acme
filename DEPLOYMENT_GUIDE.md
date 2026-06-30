# ACME Agents Deployment & Usage Guide

This guide details how to develop, deploy, and interact with the ACME Media Campaign and Customer Support system.

---

## 🛠️ Prerequisites & Setup

### 1. Google Cloud Setup
Ensure you have the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed and authenticated:
```bash
# Login to GCP
gcloud auth login
gcloud auth application-default login

# Set your active project ID
gcloud config set project <YOUR-PROJECT-ID>
```

### 2. Enable Required APIs
Enable the Vertex AI and BigQuery APIs:
```bash
gcloud services enable aiplatform.googleapis.com bigquery.googleapis.com run.googleapis.com artifactregistry.googleapis.com
```

---

## 💻 Local Development

### 1. Start the Marketing Agent Backend
Go to the `marketing-agent` folder and run the FastAPI server:
```bash
cd marketing-agent
uv run fastapi dev app/fast_api_app.py --port 8000
```

### 2. Start the Customer Agent Backend
Go to the `customer-agent` folder and run its FastAPI server:
```bash
cd customer-agent
uv run fastapi dev customer_app/fast_api_app.py --port 8080
```

### 3. Start the React Frontend
Go to the `frontend` folder, install dependencies, and start the development server:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🚀 Cloud Run Deployment

All deployment packages are optimized using `.gcloudignore` files to prevent uploading unnecessary virtual environments (`.venv/`) and packages (`node_modules/`).

### 1. Deploy the Marketing Agent Backend
```bash
cd marketing-agent
gcloud run deploy marketing-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

### 2. Deploy the Customer Agent Backend
```bash
cd customer-agent
gcloud run deploy customer-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

### 3. Deploy the React Frontend
```bash
cd frontend
gcloud run deploy marketing-frontend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

---

## 💡 How to Use & Verify Features

### 1. Core Campaign Generation
- Enter a marketing proposal topic (e.g. `"Suggest a marketing campaign based on climate change"`) in the main workspace input.
- Click **Send**.
- Watch the **Stage Progress Bar** progress through the workflow:
  - `Planner Stage`: Routing your query and extracting keywords.
  - `Data Extraction Stage`: Concurrently querying BigQuery and fetching Google Trends.
  - `Generator Stage`: Feeding cleaned metrics to the campaign generator.
  - `Critic Stage`: Inspecting recommendations and enforcing loop quality.

### 2. Real-Time Country Trends Check
- Enter a query targeting a specific country (e.g. `"Suggest a campaign based on trends in Japan"`).
- The query will automatically redirect to fetch raw top-rank trends directly from the targeted region, rendering accurate local keyword graphs instead of blank empty charts.

### 3. Customer Support Chatbot
- Click the floating chat bubble widget in the bottom-right corner.
- Chat with the customer assistant.
- Tell it `"I'm bored"`, and it will query the internal BigQuery database, fetching the top high-sentiment podcast recommendations showing explicit scores (e.g., `sentiment score: 0.92`).
