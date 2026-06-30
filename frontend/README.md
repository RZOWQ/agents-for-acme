# ACME Media Campaign and Support Dashboard

A React single page dashboard that interfaces with both the **Marketing Agent** and the **Customer Support Agent**.

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── CustomerSupportWidget.jsx  # Customer support floating chat box
│   │   └── MarkdownComponents.jsx     # Renders inline Vega-Lite, metric cards, and banners
│   ├── App.jsx                        # Main layout and campaign workspace
│   ├── App.css                        # Glassmorphic layout styling
│   ├── index.css                      # Global design system style tokens
│   └── main.jsx                       # Entrypoint mount
├── index.html
├── package.json
└── vite.config.js
```

## Features

- **Vega-Lite Live Chart Embedding:** Renders trends (line charts), allocations (donut charts), and views (bar charts) programmatically.
- **Stage Progress Bar:** Displays detailed agent workflow steps (Planner -> BQ Fetching -> Generator -> Critic review loops) in real-time.
- **Customer Support Floating Widget:** Direct chat bridge connecting to the customer-agent service.
- **Premium Glassmorphic UI:** Aesthetic, modern, high-contrast dark layout theme.

## Development & Test Commands

Start Vite dev server locally:
```bash
npm run dev
```

Build production static assets:
```bash
npm run build
```
