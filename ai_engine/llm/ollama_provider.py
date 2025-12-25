"""Ollama LLM provider implementation."""

import os
from typing import List, Dict
import httpx

from .base import LLMProvider


class OllamaProvider(LLMProvider):
    """Ollama LLM provider using local Ollama server."""

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self._model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
        self.timeout = 60.0

    @property
    def model_name(self) -> str:
        return self._model

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> str:
        """Generate chat response using Ollama."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self._model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "top_p": top_p,
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()
                return result.get("message", {}).get("content", "")
        except Exception as e:
            print(f"Ollama chat error: {e}")
            raise

    async def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate text using Ollama."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self._model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
        except Exception as e:
            print(f"Ollama generate error: {e}")
            raise
