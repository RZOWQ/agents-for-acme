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
import time
import asyncio
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional

from google.adk.plugins.base_plugin import BasePlugin
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from google.cloud import firestore as firestore_module

logger = logging.getLogger(__name__)

# Cacheable agents — only deterministic input→output agents benefit from caching
_CACHEABLE_AGENTS = {"planner_agent", "sql_generator_agent", "conversational_agent"}

class CachingPlugin(BasePlugin):
    """Firestore-backed response cache using ADK before/after model callbacks.

    Cache key: SHA256(agent_name + '::' + normalised user query)
    Cache hit:  returns a synthetic LlmResponse, skipping Vertex AI entirely.
    Cache miss: stores the response after a successful model call.
    TTL:        configurable via CACHE_TTL_SECONDS env var (default 3600 = 1h).
    """

    def __init__(self, name: str = "caching_plugin"):
        super().__init__(name=name)
        self._db: Optional[firestore_module.AsyncClient] = None
        self._collection = os.environ.get("CACHE_COLLECTION", "marketing_agent_cache_v4")
        self._ttl_seconds = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))

    def _get_db(self) -> firestore_module.AsyncClient:
        """Lazily initialise the Firestore async client."""
        if self._db is None:
            self._db = firestore_module.AsyncClient()
        return self._db

    @staticmethod
    def _make_cache_key(agent_name: str, llm_request: LlmRequest) -> str:
        """Derive a stable cache key from the agent name and all text components of the request."""
        extracted_texts = []
        
        try:
            contents = llm_request.contents or []
            for content in contents:
                parts = getattr(content, "parts", []) or []
                for part in parts:
                    text = getattr(part, "text", None)
                    if text:
                        extracted_texts.append(text)
        except Exception as e:
            logger.warning(f"[Cache Key] Error parsing contents: {e}")

        try:
            if llm_request.system_instruction:
                parts = getattr(llm_request.system_instruction, "parts", []) or []
                for part in parts:
                    text = getattr(part, "text", None)
                    if text:
                        extracted_texts.append(text)
        except Exception as e:
            logger.warning(f"[Cache Key] Error parsing system instructions: {e}")

        raw_query = " ".join(extracted_texts) if extracted_texts else str(llm_request)
        
        # Normalise white spaces and casing
        normalised = " ".join(raw_query.lower().split())
        payload = f"{agent_name}::{normalised}"
        
        return hashlib.sha256(payload.encode()).hexdigest()

    async def before_model_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_request: LlmRequest,
    ) -> Optional[LlmResponse]:
        agent_name = getattr(callback_context, "agent_name", None) or ""
        if agent_name not in _CACHEABLE_AGENTS:
            return None

        cache_key = self._make_cache_key(agent_name, llm_request)
        
        callback_context.state["current_cache_key"] = cache_key
        
        try:
            db = self._get_db()
            doc = await db.collection(self._collection).document(cache_key).get()
            if doc.exists:
                data = doc.to_dict()
                expires_at = data.get("expires_at")
                if expires_at and datetime.now(timezone.utc) < expires_at:
                    cached_text = data.get("response_text", "")
                    logger.info(f"[Cache HIT] agent={agent_name} key={cache_key[:12]}...")
                    return LlmResponse(
                        content=types.Content(
                            role="model",
                            parts=[types.Part.from_text(text=cached_text)],
                        )
                    )
                else:
                    logger.info(f"[Cache EXPIRED] agent={agent_name} key={cache_key[:12]}...")
        except Exception as e:
            logger.warning(f"[Cache] Firestore read error: {e}")
        return None

    async def after_model_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_response: LlmResponse,
    ) -> Optional[LlmResponse]:
        agent_name = getattr(callback_context, "agent_name", None) or ""
        if agent_name not in _CACHEABLE_AGENTS:
            return None

        try:
            parts = getattr(llm_response.content, "parts", []) or []
            response_text = next(
                (getattr(p, "text", None) for p in parts if getattr(p, "text", None)),
                None,
            )
            if not response_text:
                return None

            cache_key = callback_context.state.get("current_cache_key")
            if not cache_key:
                return None

            expires_at = datetime.now(timezone.utc) + timedelta(seconds=self._ttl_seconds)
            db = self._get_db()
            await db.collection(self._collection).document(cache_key).set({
                "agent_name": agent_name,
                "response_text": response_text,
                "expires_at": expires_at,
                "created_at": datetime.now(timezone.utc),
            })
            logger.info(f"[Cache STORE] agent={agent_name} key={cache_key[:12]}... ttl={self._ttl_seconds}s")
        except Exception as e:
            logger.warning(f"[Cache] Firestore write error: {e}")
        return None

class ThrottlingPlugin(BasePlugin):
    def __init__(self, min_delay_seconds: float = 1.5, name: str = "throttling_plugin"):
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
