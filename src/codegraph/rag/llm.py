"""LLM provider abstraction and implementations for Graph-RAG reasoning."""

from abc import ABC, abstractmethod
import json
import re
from typing import Any


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate string response for input prompt."""
        pass


class FakeLLMProvider(BaseLLMProvider):
    """Deterministic mock LLM provider for unit testing without external API calls."""

    def __init__(self, default_response: str | None = None) -> None:
        self.default_response = default_response
        self.last_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.last_prompt = prompt
        if self.default_response is not None:
            return self.default_response

        # Check if prompt requests query analysis JSON
        if "JSON" in prompt or "intent_type" in prompt:
            # Simple mock intent
            return json.dumps(
                {
                    "intent_type": "symbol_lookup",
                    "entities": ["UserService", "create_user"],
                    "concepts": ["user creation"],
                    "requested_relationships": ["CALLS"],
                }
            )

        # Mock grounded answer with valid citations [E1]
        if "[E1]" in prompt or "EVIDENCE" in prompt:
            return (
                "The `UserService.create_user` method delegates user creation and persistence. [E1] "
                "It uses `UserRepository.create` to store the new user entity. [E1]"
            )

        return "Mock grounded response. [E1]"


class OpenAICompatibleProvider(BaseLLMProvider):
    """LLM provider using OpenAI-compatible REST API (e.g. Ollama, vLLM, LocalAI, OpenAI)."""

    def __init__(
        self,
        api_key: str = "mock-key",
        base_url: str = "http://localhost:11434/v1",
        model: str = "qwen2.5-coder",
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate(self, prompt: str) -> str:
        import urllib.request

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"LLM API request failed: {e}") from e
