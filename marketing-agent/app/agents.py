# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.adk.agents import LlmAgent
from app.model_utils import MultiRegionGemini
from app.schemas import PlannerOutput, CampaignProposal, CriticOutput

planner_agent = LlmAgent(
    name="planner_agent",
    model=MultiRegionGemini(model="gemini-2.5-flash-lite"),
    instruction="""Route the user request strictly to one of these:
- 'internal_bq': For queries about "our content", "podcast library", internal data, or "what we have".
- 'google_trends': For external topics, news, or global trends.
- 'both': When comparing internal content against external trends.
- 'conversational': For greetings or generic chat not requiring data.

For trends, set search_term and expand short acronyms (e.g., 'AI' → 'Artificial Intelligence').""",
    output_schema=PlannerOutput,
)

sql_generator_agent = LlmAgent(
    name="sql_generator_agent",
    model=MultiRegionGemini(model="gemini-2.5-flash-lite"),
    instruction="""Output a raw SELECT-only SQL query (no markdown) for `acme_media.podcast_performance` (fields: episode_id, title, category, views, likes, shares, sentiment_score). 

- If the user asks for specific topics (e.g., "[Topic]"), you MUST use case-insensitive substring matching on BOTH `title` and `category` fields:
  - e.g., `LOWER(title) LIKE '%[keyword]%' OR LOWER(category) LIKE '%[keyword]%'`
  - Always brainstorm 2-3 key synonyms or root words (e.g., [Topic] -> '%[keyword1]%', '%[keyword2]%') and combine them with OR.
  - Never use strict equality (=) or search only one field.
- If the user's prompt is broad (e.g., "what contents we have" or "suggest a campaign" without a specific topic), do NOT use a WHERE clause. Instead, return the highest performing content overall by using `ORDER BY views DESC LIMIT 5`.

Output ONLY the SQL string.""",
)

proposal_generator_agent = LlmAgent(
    name="proposal_generator_agent",
    model=MultiRegionGemini(model="gemini-2.5-flash-lite"),
    instruction="""Generate a CampaignProposal backed by the provided data. Include 3-4 supporting_ui_elements. Follow ALL rules below exactly.

**GLOBAL RULES**
- All chart titles MUST be decision questions (e.g. "When is [Topic] interest peaking?").
- Every chart MUST have a non-empty insight_caption: one concrete actionable sentence.
- Do NOT include top-level "width" or "height" keys in any vega_spec.
- Do NOT repeat the title inside vega_spec; the frontend renders it separately.

--- CHART 1: Trends Over Time (REQUIRED when trends data present AND rows contain a "week" field) ---
- component_type: line_chart
- The Google Trends rows have exactly these fields: term, rank, score, week, country_name, region_name
- Vega-Lite spec:
  - mark: "line"
  - data.values: up to 5 of the actual rows (use the week and score values from the data)
  - encoding.x: {field: "week", type: "temporal", title: "Week", axis: {format: "%b %d", labelAngle: -30}}
  - encoding.y: {field: "score", type: "quantitative", title: "Interest Score"}
  - encoding.color: {field: "country_name", type: "nominal", title: "Country"}
- insight_caption: state the peak week and the specific recommended campaign launch window.

--- CHART 2: Internal Content Performance (REQUIRED when BQ data present) ---
- component_type: bar_chart
- The BQ rows have exactly these fields: episode_id, title, category, views, likes, shares, sentiment_score
- Vega-Lite spec:
  - mark: "bar"
  - data.values: up to 5 BQ rows as-is
  - encoding.x: {field: "views", type: "quantitative", title: "Views"}
  - encoding.y: {field: "title", type: "nominal", title: "Episode", sort: "-x"}
- insight_caption: name the top episode and its key metric.

--- CHART 3: Channel Allocation Donut (REQUIRED, ALWAYS) ---
- component_type: donut_chart
- Set marketing_channels and channel_allocations in the proposal (keys must match exactly, percentages must sum to 100).
- Allocate strategically based on the campaign context — do NOT use equal splits:
  - Live sports / major events: Social Media 45%, Video Ads 30%, Newsletter 15%, Events 10%
  - B2B / professional content: Email 40%, LinkedIn 30%, Podcast Ads 20%, Events 10%
  - Youth / entertainment: Social Media 50%, Influencer 25%, Audio Ads 15%, Newsletter 10%
  - Adjust these templates to fit the specific audience and campaign tone.
- insight_caption: name the top 2 channels and explain WHY those percentages fit this specific audience.

--- CHART 4: Engagement Quality Scatter (OPTIONAL — only if BQ rows have sentiment_score) ---
- component_type: scatter_chart
- Vega-Lite spec:
  - mark: {type: "point", size: 80}
  - data.values: BQ rows
  - encoding.x: {field: "views", type: "quantitative"}
  - encoding.y: {field: "sentiment_score", type: "quantitative"}
  - encoding.tooltip: [{field: "title", type: "nominal"}]
- insight_caption: call out the hidden gem (high sentiment, low views).

--- METRIC CARD (REQUIRED) ---
- component_type: metric_card
- metric_value: a computed stat string (e.g. "+340% trend surge this week", "Top episode: 52K views").""",
    output_schema=CampaignProposal,
)

critic_agent = LlmAgent(
    name="critic_agent",
    model=MultiRegionGemini(model="gemini-2.5-flash-lite"),
    instruction="""Evaluate the campaign proposal against the user query and retrieved data. Check ONLY these content-quality criteria:
1. TOPIC ALIGNMENT: Does the campaign_title, concept, and target_audience directly address the user's query? Reject if off-topic.
2. DATA CITATIONS: Only apply this check if the provided Trends data or BQ data contains at least one row. If both are empty or missing rows, SKIP this check and do not reject for it. When data IS present, the ad copy and actionable_items must reference at least one specific number or stat from it.
3. METRIC CARD: Is there at least one metric_card element with a non-empty metric_value? Reject if missing.

Do NOT check chart structure, vega_spec contents, insight_caption presence, or chart types — these are handled automatically by the system.
Do NOT suggest the proposal include hypothetical or made-up data.
Approve if all applicable checks pass. Set is_approved=False only for genuine content failures, with concise feedback on what specifically to fix.""",
    output_schema=CriticOutput,
)

refiner_agent = LlmAgent(
    name="refiner_agent",
    model=MultiRegionGemini(model="gemini-2.5-flash-lite"),
    instruction="""Rewrite the proposal to fix exactly what the Critic flagged. Rules:
- Fix topic alignment: ensure campaign_title, concept, and target_audience directly address the user's original query.
- Add data citations: weave specific numbers from the provided Trends/BQ data into the ad copy and actionable_items (e.g. mention actual scores, view counts, dates).
- Fix metric_card: if a metric_card is missing or has an empty metric_value, add one with a concrete computed stat.
- PRESERVE all supporting_ui_elements exactly as-is — do NOT change component_type, vega_spec, or any chart fields. Charts are generated programmatically and must not be touched.""",
    output_schema=CampaignProposal,
)

conversational_agent = LlmAgent(
    name="conversational_agent",
    model=MultiRegionGemini(model="gemini-2.5-flash-lite"),
    instruction="Friendly ACME Marketing Assistant. Help users generate data-backed campaigns (internal podcast data or Google Trends). Answer general questions concisely.",
)
