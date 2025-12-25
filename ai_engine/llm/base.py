"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> str:
        """Generate a chat response from messages.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            temperature: Sampling temperature (0.0 to 1.0).
            top_p: Top-p sampling parameter.

        Returns:
            The generated response text.
        """
        pass

    @abstractmethod
    async def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate text from a prompt.

        Args:
            prompt: The text prompt.
            temperature: Sampling temperature (0.0 to 1.0).

        Returns:
            The generated response text.
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the name of the model being used."""
        pass
