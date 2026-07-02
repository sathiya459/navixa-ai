"""Provider abstraction for NAVIXA InsightAI (Section 15).

Every provider implements a single `complete` method; all prompt
construction lives in prompts.py so switching providers never requires
touching call sites or endpoints. All AI calls happen server-side only
(Section 7) - the frontend never sees a provider API key.
"""

from abc import ABC, abstractmethod


class AIProviderError(RuntimeError):
    """Raised when a provider is unavailable (missing config) or a call fails."""


class AIProvider(ABC):
    name: str

    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Returns the model's text completion for the given prompt pair."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Whether this provider has the credentials needed to make calls."""
