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
            query_match = re.search(r'User Query:\s*"([^"]+)"', prompt)
            query = query_match.group(1) if query_match else prompt
            raw_entities = re.findall(r"[A-Za-z_][A-Za-z0-9_\.]*", query)
            stop_words = {
                "who", "what", "where", "how", "why", "does", "is", "a", "an", "the", "in", "from",
                "and", "or", "to", "for", "with", "call", "calls", "calling", "inherit", "inherits",
                "import", "imports", "show", "find", "locate", "defined", "definition", "implemented",
                "function", "class", "method", "module", "file", "code"
            }
            entities = [e for e in raw_entities if e.lower() not in stop_words and len(e) >= 2]
            if ("create" in query.lower() or "users" in query.lower()) and "create_user" not in entities:
                entities.append("create_user")

            return json.dumps(
                {
                    "intent_type": "symbol_lookup",
                    "entities": entities if entities else ["UserService"],
                    "concepts": [],
                    "requested_relationships": [],
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
    """LLM provider using OpenAI-compatible REST API (e.g. Ollama, vLLM, LocalAI, OpenAI, NVIDIA NIM)."""

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


class NvidiaLLMProvider(OpenAICompatibleProvider):
    """NVIDIA NIM Cloud API LLM Provider."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        model: str = "meta/llama-3.3-70b-instruct",
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> None:
        import os
        key = api_key or os.getenv("NVIDIA_API_KEY") or os.getenv("NVAPI_KEY", "")
        super().__init__(
            api_key=key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

