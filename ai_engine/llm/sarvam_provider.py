"""Sarvam AI LLM provider using Sarvam-M model."""

import os
import httpx
from typing import List, Dict, Any, Optional, AsyncGenerator

from .base import LLMProvider


class SarvamProvider(LLMProvider):
    """Sarvam AI LLM provider using Sarvam-M model.

    Sarvam-M is a 24B parameter model optimized for Indian languages:
    - 10 Indic languages + English
    - Code-mixing support (Hinglish)
    - Hybrid thinking mode for complex reasoning
    - Wikipedia grounding for factual queries

    API Docs: https://docs.sarvam.ai/api-reference-docs/chat/completions
    """

    BASE_URL = "https://api.sarvam.ai"

    def __init__(self):
        self.api_key = os.getenv("SARVAM_API_KEY")
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY environment variable is required")

        self.model = os.getenv("SARVAM_LLM_MODEL", "sarvam-m")

        self.headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }

    @property
    def model_name(self) -> str:
        return self.model

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 500,
        thinking_mode: Optional[str] = None,
    ) -> str:
        """Generate a chat response.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            temperature: Sampling temperature (0.0 to 2.0).
            top_p: Top-p sampling parameter.
            max_tokens: Maximum tokens to generate.
            thinking_mode: Enable thinking mode ('low', 'medium', 'high') for complex reasoning.

        Returns:
            The generated response text.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "stream": False,
        }

        # Enable thinking mode for complex queries
        if thinking_mode:
            payload["reasoning_effort"] = thinking_mode

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/v1/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=60.0
                )

                if response.status_code != 200:
                    print(f"[Sarvam LLM] Error {response.status_code}: {response.text}")
                    raise Exception(f"Sarvam LLM error: {response.text}")

                result = response.json()

                # Extract response text
                choices = result.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")

                return ""

        except Exception as e:
            print(f"[Sarvam LLM] Error: {e}")
            raise

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> AsyncGenerator[str, None]:
        """Stream chat response tokens.

        Yields tokens as they are generated for lower latency.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self.BASE_URL}/v1/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=60.0
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break

                            import json
                            try:
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            print(f"[Sarvam LLM Stream] Error: {e}")
            raise

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        """Generate text from a prompt.

        Wraps the prompt in a user message and calls chat().
        """
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, temperature=temperature, max_tokens=max_tokens)

    async def chat_with_grounding(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
        """Chat with Wikipedia grounding for factual queries.

        Uses RAG to retrieve relevant Wikipedia content.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "wiki_grounding": True,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/v1/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=60.0
                )

                response.raise_for_status()
                result = response.json()

                choices = result.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")

                return ""

        except Exception as e:
            print(f"[Sarvam LLM Grounding] Error: {e}")
            raise
