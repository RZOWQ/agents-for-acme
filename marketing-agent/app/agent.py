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
from google.adk.apps import App
from google.adk.workflow import Workflow, FunctionNode, JoinNode, START, Edge

# Initialise environment variables
_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-east4"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# Import agents
from app.agents import (
    planner_agent,
    sql_generator_agent,
    proposal_generator_agent,
    critic_agent,
    refiner_agent,
    conversational_agent,
)

# Import functional nodes
from app.nodes import (
    planner_node,
    conversational_node,
    retrieve_trends_node,
    retrieve_bq_node,
    generator_node,
    critic_node,
    refiner_node,
    format_output_node,
)

# Import plugins
from app.plugins import CachingPlugin, ThrottlingPlugin

# Wrap function nodes for Workflow DAG
planner_node_node = FunctionNode(func=planner_node, name="planner_node", rerun_on_resume=True)
conversational_node_node = FunctionNode(func=conversational_node, name="conversational_node", rerun_on_resume=True)
retrieve_trends_node_node = FunctionNode(func=retrieve_trends_node, name="retrieve_trends_node")
retrieve_bq_node_node = FunctionNode(func=retrieve_bq_node, name="retrieve_bq_node", rerun_on_resume=True)
generator_node_node = FunctionNode(func=generator_node, name="generator_node", rerun_on_resume=True)
critic_node_node = FunctionNode(func=critic_node, name="critic_node", rerun_on_resume=True)
refiner_node_node = FunctionNode(func=refiner_node, name="refiner_node", rerun_on_resume=True)
format_output_node_node = FunctionNode(func=format_output_node, name="format_output_node")

join_node = JoinNode(name="join_node")

# Define ADK 2.0 Workflow
root_agent = Workflow(
    name="marketing_agent_v2",
    edges=[
        Edge(from_node=START, to_node=planner_node_node),
        
        # Route depending on the planner's decision
        Edge(from_node=planner_node_node, to_node=retrieve_trends_node_node, route="data_path"),
        Edge(from_node=planner_node_node, to_node=retrieve_bq_node_node, route="data_path"),
        Edge(from_node=planner_node_node, to_node=conversational_node_node, route="conversational"),
        
        # Fan-in via join_node
        Edge(from_node=retrieve_trends_node_node, to_node=join_node),
        Edge(from_node=retrieve_bq_node_node, to_node=join_node),
        
        # Proposal generation and review loop
        Edge(from_node=join_node, to_node=generator_node_node),
        Edge(from_node=generator_node_node, to_node=critic_node_node),
        
        # Critic loop pathways
        Edge(from_node=critic_node_node, to_node=refiner_node_node, route="reject"),
        Edge(from_node=refiner_node_node, to_node=critic_node_node),
        Edge(from_node=critic_node_node, to_node=format_output_node_node, route="approve"),
    ]
)

# Export App
app = App(
    root_agent=root_agent,
    name="app",
    plugins=[
        CachingPlugin(),
        ThrottlingPlugin(min_delay_seconds=1.5),
    ]
)
