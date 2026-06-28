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

import json
from typing import Any
from google.adk.events.event import Event
from google.adk.agents.context import Context
from google.adk.workflow import FunctionNode
from google.genai import types

from app.tools import query_bigquery, check_google_trends
from app.agents import (
    planner_agent,
    sql_generator_agent,
    proposal_generator_agent,
    critic_agent,
    refiner_agent,
    conversational_agent,
)

# Workflow Function Nodes
async def planner_node(ctx: Context, node_input: Any) -> Event:
    # Clear stale data from any previous request so it never leaks into this turn
    ctx.state["trends_data"] = None
    ctx.state["bq_data"] = None

    prompt = ""
    if isinstance(node_input, str):
        prompt = node_input
    elif hasattr(node_input, "parts") and node_input.parts:
        prompt = node_input.parts[0].text
    else:
        prompt = str(node_input)
    
    res = await ctx.run_node(planner_agent, node_input=prompt)
    
    route_val = getattr(res, "route", "both") if not isinstance(res, dict) else res.get("route", "both")
    term_val = getattr(res, "search_term", "") if not isinstance(res, dict) else res.get("search_term", "")
    
    # Unified route trigger for any data-fetching path
    dag_route = "data_path" if route_val in ["google_trends", "internal_bq", "both"] else "conversational"
    
    return Event(
        output=prompt, 
        route=dag_route, 
        state={"search_term": term_val, "original_query": prompt, "planner_route": route_val}
    )

async def critic_node(ctx: Context, node_input: Any) -> Event:
    proposal = ctx.state.get("proposal")
    trends_data = ctx.state.get("trends_data")
    bq_data = ctx.state.get("bq_data")
    loop_count = ctx.state.get("loop_count", 0)
    
    input_str = f"Proposal: {proposal}\nTrends: {trends_data}\nBQ: {bq_data}"
    critic_res = await ctx.run_node(critic_agent, node_input=input_str)
    
    is_approved = getattr(critic_res, "is_approved", True) if not isinstance(critic_res, dict) else critic_res.get("is_approved", True)
    feedback = getattr(critic_res, "feedback", "") if not isinstance(critic_res, dict) else critic_res.get("feedback", "")
    
    if is_approved or loop_count >= 1:
        return Event(output=proposal, route="approve")
    else:
        return Event(output=feedback, route="reject", state={"feedback": feedback, "loop_count": loop_count + 1})

async def conversational_node(ctx: Context, node_input: Any) -> Event:
    res = await ctx.run_node(conversational_agent, node_input=node_input)
    reply = res.parts[0].text if hasattr(res, "parts") else str(res)
    yield Event(content=types.Content(role='model', parts=[types.Part.from_text(text=reply)]))
    yield Event(output=reply)

async def retrieve_trends_node(ctx: Context, node_input: str) -> Event:
    planner_route = ctx.state.get("planner_route", "both")
    if planner_route not in ["google_trends", "both"]:
        return Event(output=None) 

    term_val = ctx.state.get("search_term", "").strip().lower()
    is_generic = term_val in ["", "none", "current trends", "trends", "recent trends", "global trends", "google trends"]
    trends_data = check_google_trends(term=None if is_generic else term_val)
    if is_generic and isinstance(trends_data, dict) and "rows" in trends_data:
        trends_data["rows"] = trends_data["rows"][:5]
    return Event(output=trends_data, state={"trends_data": trends_data})

async def retrieve_bq_node(ctx: Context, node_input: str) -> Event:
    planner_route = ctx.state.get("planner_route", "both")
    if planner_route not in ["internal_bq", "both"]:
        return Event(output=None) 

    sql_res = await ctx.run_node(sql_generator_agent, node_input=node_input)
    sql_query = sql_res.parts[0].text.strip() if hasattr(sql_res, "parts") else str(sql_res)
    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
    bq_data = query_bigquery(sql_query)
    if isinstance(bq_data, dict) and "rows" in bq_data:
        bq_data["rows"] = bq_data["rows"][:5]
    return Event(output=bq_data, state={"bq_data": bq_data})

async def generator_node(ctx: Context, node_input: Any) -> Event:
    original_query = ctx.state.get("original_query", "")
    trends_data = ctx.state.get("trends_data")
    bq_data = ctx.state.get("bq_data")
    
    clean_trends = []
    if trends_data and isinstance(trends_data, dict) and "rows" in trends_data:
        for r in trends_data["rows"][:5]:
            clean_trends.append({k: v for k, v in r.items() if k in ["term", "score", "week", "country_name", "region_name", "dma_name"]})
            
    clean_bq = []
    if bq_data and isinstance(bq_data, dict) and "rows" in bq_data:
        for r in bq_data["rows"][:5]:
            clean_bq.append({k: v for k, v in r.items() if k in ["title", "views", "likes", "sentiment_score"]})
            
    input_str = f"Query: {original_query}\nTrends Data: {clean_trends}\nBQ Data: {clean_bq}"
    proposal = await ctx.run_node(proposal_generator_agent, node_input=input_str)
    return Event(output=proposal, state={"proposal": proposal})

async def refiner_node(ctx: Context, node_input: str) -> Event:
    proposal = ctx.state.get("proposal")
    feedback = node_input
    
    input_str = f"Original Proposal: {proposal}\nFeedback: {feedback}"
    refined_proposal = await ctx.run_node(refiner_agent, node_input=input_str)
    return Event(output=refined_proposal, state={"proposal": refined_proposal})

async def format_output_node(ctx: Context, node_input: Any) -> Event:
    p = ctx.state.get("proposal")
    if not p:
        p = node_input
        
    def get_val(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    md = f"""## Campaign: {get_val(p, 'campaign_title')}

**Concept**: {get_val(p, 'concept')}

**Target Audience**: {get_val(p, 'target_audience')}

**Suggested Social Media Ad Copy**:
{get_val(p, 'suggested_social_media_ad_copy')}

**Actionable Items**:
"""
    for item in get_val(p, 'actionable_items') or []:
        md += f"* {item}\n"
        
    md += "\n**Marketing Channels**:\n"
    for chan in get_val(p, 'marketing_channels') or []:
        md += f"* {chan}\n"
        
    md += "\n**KPI Metrics to Track**:\n"
    for kpi in get_val(p, 'kpi_metrics') or []:
        md += f"* {kpi}\n"
        
    md += "\n**Supporting Visuals**:\n"
    
    trends_data = ctx.state.get("trends_data") or {}
    trends_rows = trends_data.get("rows", []) if isinstance(trends_data, dict) else []
    bq_data = ctx.state.get("bq_data") or {}
    bq_rows = bq_data.get("rows", []) if isinstance(bq_data, dict) else []
    channels = get_val(p, 'marketing_channels') or []

    emitted_line = False
    emitted_donut = False
    emitted_bar = False
    emitted_scatter = False

    for elem in get_val(p, 'supporting_ui_elements') or []:
        elem_type = get_val(elem, 'component_type')
        title = get_val(elem, 'title') or ''
        caption = get_val(elem, 'insight_caption') or ''

        if elem_type == 'line_chart' and not emitted_line:
            emitted_line = True
            values = [
                {"week": r["week"], "score": r.get("score", 0), "country_name": r.get("country_name") or r.get("dma_name", "Global")}
                for r in trends_rows if "week" in r and r.get("week")
            ]
            unique_weeks = set(v["week"] for v in values)
            if len(unique_weeks) <= 1 and values:
                top = max(values, key=lambda v: v["score"])
                bar_title = "Which countries are most interested?"
                bar_caption = (
                    f"{top['country_name']} leads with an interest score of {top['score']}. "
                    "Focus initial campaign spend and localisation here first."
                )
                spec = {
                    "title": bar_title,
                    "mark": "bar",
                    "data": {"values": values},
                    "encoding": {
                        "x": {"field": "score", "type": "quantitative", "title": "Interest Score", "scale": {"domain": [0, 100], "clamp": True, "nice": False}},
                        "y": {"field": "country_name", "type": "nominal", "title": "Country", "sort": "-x"}
                    },
                    "_caption": bar_caption
                }
            else:
                spec = {
                    "title": title,
                    "mark": {"type": "line", "point": True},
                    "data": {"values": values if values else [{"week": "2026-06-01", "score": 0, "country_name": "N/A"}]},
                    "encoding": {
                        "x": {"field": "week", "type": "temporal", "title": "Week",
                              "axis": {"format": "%b %d", "labelAngle": -30}},
                        "y": {"field": "score", "type": "quantitative", "title": "Interest Score"},
                        "color": {"field": "country_name", "type": "nominal", "title": "Country"}
                    }
                }
                if caption:
                    spec["_caption"] = caption
            md += f"\n```vega-lite\n{json.dumps(spec, indent=2)}\n```\n"

        elif elem_type == 'donut_chart' and not emitted_donut:
            emitted_donut = True
            allocations = get_val(p, 'channel_allocations') or {}
            if channels and allocations:
                values = [{"channel": ch, "pct": int(allocations.get(ch, 100 // len(channels)))} for ch in channels]
                total = sum(v["pct"] for v in values)
                if total != 100 and total > 0:
                    values = [{"channel": v["channel"], "pct": round(v["pct"] * 100 / total)} for v in values]
            elif channels:
                n = len(channels)
                base = 100 // n
                remainder = 100 - base * n
                pcts = [base + (1 if i < remainder else 0) for i in range(n)]
                values = [{"channel": ch, "pct": pct} for ch, pct in zip(channels, pcts)]
            else:
                values = [
                    {"channel": "Social Media", "pct": 40},
                    {"channel": "Audio Ads", "pct": 30},
                    {"channel": "Newsletter", "pct": 20},
                    {"channel": "Events", "pct": 10},
                ]
            spec = {
                "title": title,
                "mark": {"type": "arc", "innerRadius": 50},
                "data": {"values": values},
                "encoding": {
                    "theta": {"field": "pct", "type": "quantitative"},
                    "color": {"field": "channel", "type": "nominal", "legend": {"title": "Channel"}}
                }
            }
            if caption:
                spec["_caption"] = caption
            md += f"\n```vega-lite\n{json.dumps(spec, indent=2)}\n```\n"

        elif elem_type == 'bar_chart' and not emitted_bar:
            emitted_bar = True
            bar_values = [
                {"title": (r.get("title") or "")[:40], "views": r.get("views") or 0}
                for r in bq_rows[:5] if r.get("title") and r.get("views") is not None
            ]
            if bar_values:
                spec = {
                    "title": title,
                    "mark": "bar",
                    "data": {"values": bar_values},
                    "encoding": {
                        "x": {"field": "views", "type": "quantitative", "title": "Views"},
                        "y": {"field": "title", "type": "nominal", "title": "Episode",
                              "sort": "-x", "axis": {"labelLimit": 200}}
                    }
                }
                if caption:
                    spec["_caption"] = caption
                md += f"\n```vega-lite\n{json.dumps(spec, indent=2)}\n```\n"

        elif elem_type == 'scatter_chart' and not emitted_scatter:
            scatter_values = [
                {"title": (r.get("title") or "")[:40],
                 "views": r.get("views") or 0,
                 "sentiment_score": r.get("sentiment_score") or 0}
                for r in bq_rows[:5]
                if r.get("title") and r.get("views") is not None and r.get("sentiment_score") is not None
            ]
            if scatter_values:
                emitted_scatter = True
                spec = {
                    "title": title,
                    "mark": {"type": "point", "size": 120, "filled": True},
                    "data": {"values": scatter_values},
                    "encoding": {
                        "x": {"field": "views", "type": "quantitative", "title": "Views"},
                        "y": {"field": "sentiment_score", "type": "quantitative", "title": "Sentiment Score"},
                        "tooltip": [
                            {"field": "title", "type": "nominal"},
                            {"field": "views", "type": "quantitative"},
                            {"field": "sentiment_score", "type": "quantitative"}
                        ]
                    }
                }
                if caption:
                    spec["_caption"] = caption
                md += f"\n```vega-lite\n{json.dumps(spec, indent=2)}\n```\n"

        elif elem_type == 'metric_card':
            card_data = {"title": title, "metric_value": get_val(elem, 'metric_value')}
            md += f"\n```metric-card\n{json.dumps(card_data, indent=2)}\n```\n"

        elif elem_type == 'alert_banner':
            banner_data = {"title": title, "text_content": get_val(elem, 'text_content')}
            md += f"\n```alert-banner\n{json.dumps(banner_data, indent=2)}\n```\n"

    if not emitted_line and trends_rows:
        values = [
            {"week": r["week"], "score": r.get("score", 0), "country_name": r.get("country_name") or r.get("dma_name", "Global")}
            for r in trends_rows[:12] if "week" in r and r.get("week")
        ]
        if values:
            unique_weeks = set(v["week"] for v in values)
            if len(unique_weeks) <= 1:
                top = max(values, key=lambda v: v["score"])
                spec = {
                    "title": "Which countries are most interested?",
                    "mark": "bar",
                    "data": {"values": values},
                    "encoding": {
                        "x": {"field": "score", "type": "quantitative", "title": "Interest Score", "scale": {"domain": [0, 100], "clamp": True, "nice": False}},
                        "y": {"field": "country_name", "type": "nominal", "title": "Country", "sort": "-x"}
                    },
                    "_caption": (
                        f"{top['country_name']} leads with an interest score of {top['score']}. "
                        "Focus initial campaign spend and localisation here first."
                    )
                }
            else:
                spec = {
                    "title": "When is peak interest?",
                    "mark": {"type": "line", "point": True},
                    "data": {"values": values},
                    "encoding": {
                        "x": {"field": "week", "type": "temporal", "title": "Week",
                              "axis": {"format": "%b %d", "labelAngle": -30}},
                        "y": {"field": "score", "type": "quantitative", "title": "Interest Score"},
                        "color": {"field": "country_name", "type": "nominal", "title": "Country"}
                    }
                }
            md += f"\n```vega-lite\n{json.dumps(spec, indent=2)}\n```\n"

    if not emitted_donut and channels:
        n = len(channels)
        base = 100 // n
        remainder = 100 - base * n
        pcts = [base + (1 if i < remainder else 0) for i in range(n)]
        values = [{"channel": ch, "pct": pct} for ch, pct in zip(channels, pcts)]
        spec = {
            "title": "How should we allocate campaign effort?",
            "mark": {"type": "arc", "innerRadius": 50},
            "data": {"values": values},
            "encoding": {
                "theta": {"field": "pct", "type": "quantitative"},
                "color": {"field": "channel", "type": "nominal", "legend": {"title": "Channel"}}
            }
        }
        md += f"\n```vega-lite\n{json.dumps(spec, indent=2)}\n```\n"

    if not emitted_bar and bq_rows:
        bar_values = [
            {"title": (r.get("title") or "")[:40], "views": r.get("views") or 0}
            for r in bq_rows[:5] if r.get("title") and r.get("views") is not None
        ]
        if bar_values:
            spec = {
                "title": "Which episodes have the most views?",
                "mark": "bar",
                "data": {"values": bar_values},
                "encoding": {
                    "x": {"field": "views", "type": "quantitative", "title": "Views"},
                    "y": {"field": "title", "type": "nominal", "title": "Episode",
                          "sort": "-x", "axis": {"labelLimit": 200}}
                }
            }
            md += f"\n```vega-lite\n{json.dumps(spec, indent=2)}\n```\n"

    yield Event(content=types.Content(role='model', parts=[types.Part.from_text(text=md)]))
    yield Event(output=p)
