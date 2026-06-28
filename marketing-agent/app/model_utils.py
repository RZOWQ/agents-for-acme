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
import random
import asyncio
import logging
from typing import ClassVar
from google.adk.models import Gemini
from google.adk.models.llm_request import LlmRequest
from google.genai import Client

logger = logging.getLogger(__name__)

class AllRegionsExhaustedError(Exception):
    """Exception raised when all Vertex AI regional endpoints in the fallback chain return 429."""
    pass

class MultiRegionGemini(Gemini):
    # Global thread-safe client cache
    _client_cache: ClassVar[dict[str, Client]] = {}

    @classmethod
    def get_client(cls, region: str) -> Client:
        if region not in cls._client_cache:
            cls._client_cache[region] = Client(vertexai=True, location=region)
        return cls._client_cache[region]

    async def generate_content_async(self, llm_request: LlmRequest, stream: bool = False):
        regions_str = os.environ.get("VERTEX_FALLBACK_REGIONS", "us-east4,us-west1,europe-west4")
        regions = [r.strip() for r in regions_str.split(",") if r.strip()]
        max_retries = int(os.environ.get("VERTEX_MAX_RETRIES_PER_REGION", "2"))
        base_delay = float(os.environ.get("VERTEX_RETRY_BASE_DELAY", "1.0"))

        last_error = None
        for region in regions:
            for attempt in range(max_retries):
                try:
                    client = self.get_client(region)
                    self.__dict__['api_client'] = client

                    async for response in super().generate_content_async(llm_request, stream):
                        yield response
                    return
                except Exception as e:
                    if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                        last_error = e
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt) * random.uniform(0.5, 1.5)
                            logger.warning(
                                f"Region '{region}' returned 429 "
                                f"(attempt {attempt + 1}/{max_retries}). "
                                f"Retrying in {delay:.2f}s..."
                            )
                            await asyncio.sleep(delay)
                        else:
                            logger.warning(
                                f"Region '{region}' exhausted after {max_retries} attempts. "
                                f"Trying next region..."
                            )
                    else:
                        raise e

        raise AllRegionsExhaustedError(
            f"All configured regional endpoints ({', '.join(regions)}) were exhausted. "
            f"Last error: {last_error}"
        ) from last_error
