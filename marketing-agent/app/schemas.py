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

from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field

class PlannerOutput(BaseModel):
    route: str = Field(description="Decide routing. Must be exactly one of: 'google_trends', 'internal_bq', 'both', 'conversational'.")
    search_term: str = Field(description="If routing to google_trends or both, the search term to query (e.g. 'world cup 2026'). Otherwise empty.")

class ChartDataValue(BaseModel):
    term: str | None = Field(default=None, description="The search term or topic (e.g. 'world cup 2026')")
    score: float | None = Field(default=None, description="The score/metric (e.g. 100)")
    title: str | None = Field(default=None, description="The episode title (e.g. 'Intro to World Cup')")
    views: float | None = Field(default=None, description="The views or play count (e.g. 5000)")
    likes: float | None = Field(default=None, description="The likes count (e.g. 250)")
    sentiment_score: float | None = Field(default=None, description="The sentiment score (e.g. 0.85)")

class ChartData(BaseModel):
    values: list[ChartDataValue] = Field(description="List of data point dictionaries, max 5 items")

class EncodingAxis(BaseModel):
    field: str = Field(description="The field name to map (e.g., 'term', 'score', 'title', 'views')")
    type: str = Field(description="The data type: 'nominal' or 'quantitative'")
    title: str = Field(description="Display title for the axis")

class ChartEncoding(BaseModel):
    x: EncodingAxis = Field(description="X-axis encoding (must be quantitative metric to avoid vertical squishing)")
    y: EncodingAxis = Field(description="Y-axis encoding (must be nominal category to list items horizontally)")

class VegaLiteChart(BaseModel):
    title: str = Field(description="Title of the chart")
    mark: str = Field(default="bar", description="Mark type (e.g., 'bar')")
    data: ChartData = Field(description="Chart dataset containing data values")
    encoding: ChartEncoding = Field(description="Axis encodings")

class UIComponentType(str, Enum):
    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    SCATTER_CHART = "scatter_chart"
    DONUT_CHART = "donut_chart"
    METRIC_CARD = "metric_card"
    ALERT_BANNER = "alert_banner"

class A2UIComponent(BaseModel):
    component_type: UIComponentType = Field(description="The type of UI component: 'bar_chart', 'line_chart', 'scatter_chart', 'donut_chart', 'metric_card', or 'alert_banner'.")
    title: str = Field(description="Title phrased as a decision question, e.g. 'When is World Cup interest peaking?' or 'Which episodes should we amplify?'")
    vega_spec: Optional[dict] = Field(default=None, description="Vega-Lite JSON spec for chart types. Do NOT include top-level width or height (the frontend sets those).")
    insight_caption: Optional[str] = Field(default=None, description="One actionable sentence connecting this chart to the campaign decision. E.g. 'Interest peaks June 29 — launch social push June 27.'")
    metric_value: Optional[str] = Field(default=None, description="A large highlighted metric value (e.g., '+24% Views') if component_type is 'metric_card'.")
    text_content: Optional[str] = Field(default=None, description="Text/alert description if component_type is 'alert_banner'.")

class CampaignProposal(BaseModel):
    campaign_title: str = Field(description="A creative name for the marketing campaign.")
    concept: str = Field(description="2-3 sentences explaining the campaign concept and justifying it with data.")
    target_audience: str = Field(description="The specific audience segment targeted by this campaign.")
    suggested_social_media_ad_copy: str = Field(description="A catchy, engaging ad copy suited for social media promotion.")
    marketing_channels: list[str] = Field(description="List of marketing channels (e.g., Social Media, Audio Ads, Newsletters).")
    channel_allocations: Dict[str, int] = Field(default_factory=dict, description="Budget allocation per channel as integer percentages. Keys must exactly match marketing_channels. Values must sum to 100.")
    kpi_metrics: list[str] = Field(description="List of key performance indicators to measure success.")
    actionable_items: list[str] = Field(description="A list of step-by-step actionable tasks/items to execute this campaign.")
    supporting_ui_elements: list[A2UIComponent] = Field(description="One or more supporting UI elements dynamically decided by the agent to visualize the data or present the campaign metrics.")

class CriticOutput(BaseModel):
    is_approved: bool = Field(description="Whether the proposal is approved. Set to False if quality improvements or corrections are needed.")
    feedback: str = Field(description="Detailed feedback describing any corrections, omissions, or enhancements needed if not approved. Otherwise leave blank.")
