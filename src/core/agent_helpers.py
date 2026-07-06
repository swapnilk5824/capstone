"""
Shared runner for specialist review agents.

Every specialist agent (security, static analysis, logic, test
coverage, docs) has the same shape:
  1. Build a diff-focused user prompt.
  2. In CODEGUARD_MODE=live, call Claude with the flag_finding tool
     and collect tool_use blocks into Finding objects.
  3. In CODEGUARD_MODE=mock (default), run a deterministic rule-based
     analyzer that mimics what the prompt asks the model to do, so
     the pipeline is reproducible without API credentials.
"""
from __future__ import annotations

import os
from typing import Any, Callable, Dict, List

from .types import Finding
from .llm_client import AnthropicClient
from ..tools.tool_schemas import ALL_REVIEW_TOOLS


def build_diff_prompt(pr: Dict[str, Any], file_filter: Callable[[Dict], bool]) -> str:
    parts = [f"PR Title: {pr['title']}", f"PR Description: {pr['description']}", ""]
    for f in pr["files"]:
        if not file_filter(f):
            continue
        parts.append(f"--- FILE: {f['path']} ({f['status']}) ---")
        parts.append(f["diff"])
        parts.append("")
    return "\n".join(parts)


def run_specialist(
    agent_name: str,
    state: Dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    mock_fn: Callable[[Dict[str, Any]], List[Finding]],
) -> List[Finding]:
    mode = os.environ.get("CODEGUARD_MODE", "mock").lower()

    if mode == "live":
        client = AnthropicClient()
        resp = client.client.messages.create(
            model=client.model,
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=ALL_REVIEW_TOOLS,
        )
        findings: List[Finding] = []
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "flag_finding":
                inp = dict(block.input)
                findings.append(Finding(agent=agent_name, **inp))
        return findings

    # mock mode: deterministic rule-based analysis
    return mock_fn(state)
