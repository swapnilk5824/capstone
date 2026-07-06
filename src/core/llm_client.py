"""
LLM client wrapper.

Two backends:
- AnthropicClient: real calls to the Anthropic Messages API (requires
  ANTHROPIC_API_KEY in the environment).
- MockClient: deterministic, rule-based responses used for offline
  demos, CI, and grading without API credentials. Mock responses are
  intentionally simple pattern-matchers over the input text so that
  sample scenarios are reproducible.

Select backend via CODEGUARD_MODE=live|mock (default: mock).
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional


class LLMClient:
    def complete(self, system: str, user: str, tools: Optional[List[Dict]] = None) -> str:
        raise NotImplementedError


class AnthropicClient(LLMClient):
    def __init__(self, model: str = "claude-sonnet-5"):
        import anthropic  # imported lazily so mock mode has zero deps

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set. Export it or run with CODEGUARD_MODE=mock."
            )
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def complete(self, system: str, user: str, tools: Optional[List[Dict]] = None) -> str:
        kwargs: Dict[str, Any] = dict(
            model=self.model,
            max_tokens=1500,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        if tools:
            kwargs["tools"] = tools
        resp = self.client.messages.create(**kwargs)
        text_parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
        return "\n".join(text_parts)


class MockClient(LLMClient):
    """Deterministic stand-in for offline/reproducible runs.

    Each agent module supplies its own `mock_rules` callback via the
    `agent_name` field embedded at the top of `user` prompts (see
    agents/*.py), so this class stays generic and agent-agnostic.
    """

    def __init__(self):
        pass

    def complete(self, system: str, user: str, tools: Optional[List[Dict]] = None) -> str:
        # The calling agent embeds a MOCK_HINT block the mock rules can
        # act on; agents parse the diff themselves and only use this
        # client to format findings consistently. See agents/*.py.
        raise NotImplementedError(
            "MockClient.complete should not be called directly; "
            "agents implement mock_analyze() for deterministic logic."
        )


def get_client() -> LLMClient:
    mode = os.environ.get("CODEGUARD_MODE", "mock").lower()
    if mode == "live":
        return AnthropicClient()
    return MockClient()
