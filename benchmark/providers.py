"""
Thin adapters so the runner can call any provider with one method:

    provider.decide(system, user) -> DecideResult(text, latency_s, usage)

SDKs are imported lazily so a missing package / key only disables that one
provider. Keys are read from environment variables:
    OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY (or GEMINI_API_KEY)
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass


@dataclass
class DecideResult:
    text: str
    latency_s: float
    usage: dict | None = None       # {"input": int, "output": int} if available
    error: str | None = None


class ProviderError(RuntimeError):
    pass


def make_provider(kind, model):
    kind = kind.lower()
    if kind == "openai":
        return OpenAIProvider(model)
    if kind == "anthropic":
        return AnthropicProvider(model)
    if kind == "google":
        return GoogleProvider(model)
    raise ValueError(f"Unknown provider kind: {kind}")


class OpenAIProvider:
    """Uses the Responses API (current path for GPT-5.x)."""
    def __init__(self, model):
        self.model = model
        self._client = None

    def _client_or_raise(self):
        if self._client is None:
            key = os.environ.get("OPENAI_API_KEY")
            if not key:
                raise ProviderError("OPENAI_API_KEY not set")
            from openai import OpenAI
            self._client = OpenAI(api_key=key)
        return self._client

    def decide(self, system, user):
        client = self._client_or_raise()
        t0 = time.time()
        try:
            r = client.responses.create(
                model=self.model,
                input=[{"role": "system", "content": system},
                       {"role": "user", "content": user}],
            )
            dt = time.time() - t0
            usage = None
            if getattr(r, "usage", None):
                usage = {"input": getattr(r.usage, "input_tokens", None),
                         "output": getattr(r.usage, "output_tokens", None)}
            return DecideResult(text=r.output_text, latency_s=dt, usage=usage)
        except Exception:
            # Fall back to Chat Completions if Responses isn't available for this model.
            r = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
            )
            dt = time.time() - t0
            usage = None
            if getattr(r, "usage", None):
                usage = {"input": r.usage.prompt_tokens,
                         "output": r.usage.completion_tokens}
            return DecideResult(text=r.choices[0].message.content,
                                latency_s=dt, usage=usage)


class AnthropicProvider:
    def __init__(self, model):
        self.model = model
        self._client = None

    def _client_or_raise(self):
        if self._client is None:
            key = os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                raise ProviderError("ANTHROPIC_API_KEY not set")
            import anthropic
            self._client = anthropic.Anthropic(api_key=key)
        return self._client

    def decide(self, system, user):
        client = self._client_or_raise()
        t0 = time.time()
        r = client.messages.create(
            model=self.model,
            max_tokens=1024,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        dt = time.time() - t0
        text = next((b.text for b in r.content if b.type == "text"), "")
        usage = None
        if getattr(r, "usage", None):
            usage = {"input": r.usage.input_tokens, "output": r.usage.output_tokens}
        return DecideResult(text=text, latency_s=dt, usage=usage)


class GoogleProvider:
    """Uses the new google-genai SDK (from google import genai)."""
    def __init__(self, model):
        self.model = model
        self._client = None

    def _client_or_raise(self):
        if self._client is None:
            key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
            if not key:
                raise ProviderError("GOOGLE_API_KEY / GEMINI_API_KEY not set")
            from google import genai
            self._client = genai.Client(api_key=key)
        return self._client

    def decide(self, system, user):
        client = self._client_or_raise()
        from google.genai import types
        t0 = time.time()
        r = client.models.generate_content(
            model=self.model,
            contents=user,
            config=types.GenerateContentConfig(system_instruction=system),
        )
        dt = time.time() - t0
        usage = None
        um = getattr(r, "usage_metadata", None)
        if um:
            usage = {"input": getattr(um, "prompt_token_count", None),
                     "output": getattr(um, "candidates_token_count", None)}
        return DecideResult(text=r.text, latency_s=dt, usage=usage)
