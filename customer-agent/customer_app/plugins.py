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

import time
import asyncio
from typing import Optional
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse

class ThrottlingPlugin(BasePlugin):
    def __init__(self, min_delay_seconds: float = 1.0, name: str = "throttling_plugin"):
        super().__init__(name=name)
        self.min_delay = min_delay_seconds
        self.last_call_time = 0.0
        self.lock = asyncio.Lock()

    async def before_model_callback(self, *, callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_call_time
            if elapsed < self.min_delay:
                sleep_time = self.min_delay - elapsed
                await asyncio.sleep(sleep_time)
            self.last_call_time = time.time()
        return None
