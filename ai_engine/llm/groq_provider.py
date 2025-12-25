"""Groq LLM provider implementation."""

import os
from typing import List, Dict
from groq import AsyncGroq

from .base import LLMProvider


class GroqProvider(LLMProvider):
    """Groq LLM provider using Groq Cloud API."""

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is required for Groq provider")

        self.client = AsyncGroq(api_key=api_key)
        self._model = os.getenv("GROQ_MODEL", "qwen-qwq-32b")

    @property
    def model_name(self) -> str:
        return self._model

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> str:
        """Generate chat response using Groq."""
        try:
            response = await self.client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=1024,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            print(f"Groq chat error: {e}")
            raise

    async def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate text using Groq (via chat API with single user message)."""
        try:
            response = await self.client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=1024,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            print(f"Groq generate error: {e}")
            raise
