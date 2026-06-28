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

import os
import google.auth
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from customer_app.tools import query_bigquery, check_google_trends
from customer_app.plugins import ThrottlingPlugin

# Environment configuration
_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-east4"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

agent_instruction = """You are the ACME Corp Media Customer Assistant.
Your core task is to chat with customers, answer their questions about media, and suggest interesting media assets or podcast episodes from our library.

You have access to two tools:
1. `query_bigquery` to search the internal ACME media library database for episodes.
   - Use the table: `acme_media.podcast_performance`
   - Fields: `episode_id` (STRING), `title` (STRING), `category` (STRING), `views` (INTEGER), `likes` (INTEGER), `shares` (INTEGER), `sentiment_score` (FLOAT)
2. `check_google_trends` to inspect recent search trends from Google Trends public data.

RULES FOR RESPONSES (Avoid human reading fatigue):
- If the user says "I'm bored" or similar, proactively suggest 2-3 highly engaging, high-sentiment podcast episodes from our library. Use `query_bigquery` and sort by `sentiment_score` DESC (or filter for `sentiment_score > 0.8`) to find the best-received episodes to entertain them.
- Be extremely brief, friendly, and conversational.
- Keep responses short: under 2-3 sentences per answer when possible.
- Minimize boilerplate text, greetings, and long introductory explanations.
- When suggesting recommendations, show ONLY a brief bulleted list of 2-3 episodes showing: *Episode Title* (Category) - *Compelling Reason (mentioning the sentiment score, e.g., 'sentiment score: 0.92')*. Avoid long paragraphs or large text blocks.
"""

root_agent = Agent(
    name="customer_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3, initialDelay=1.0, maxDelay=5.0),
    ),
    instruction=agent_instruction,
    tools=[query_bigquery, check_google_trends],
)

app = App(
    root_agent=root_agent,
    name="customer_app",
    plugins=[ThrottlingPlugin(min_delay_seconds=1.0)]
)
