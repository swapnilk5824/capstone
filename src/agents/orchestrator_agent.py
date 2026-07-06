"""
Orchestrator Agent

Role: supervises the graph. Runs twice:
  - `plan`   (after ingestion, before fan-out): decides which
             specialist agents are relevant given the file mix, and
             records that reasoning for the audit trail. In this
             capstone all five specialists always run, but the hook
             is real — e.g. a docs-only PR could skip security/logic.
  - `finalize` (after the reporter): applies merge policy on top of
             the reporter's decision, e.g. auto-approve small
             docs-only PRs, or require human sign-off on any BLOCK.
"""
from __future__ import annotations

from typing import Any, Dict


SYSTEM_PROMPT = """You are the Orchestrator Agent supervising a team of specialist
code review agents (security, static analysis, logic, test coverage, docs) plus
a reporter agent. Before review, decide which specialists are relevant to this
PR's file mix and record why. After the reporter produces a decision, apply
merge policy: any BLOCK requires human sign-off; REQUEST_CHANGES requires the
author to address major findings; APPROVE/APPROVE_WITH_COMMENTS can proceed."""


def plan(state: Dict[str, Any]) -> Dict[str, Any]:
    pr = state["pr"]
    counts = pr["file_counts"]
    reasoning = []
    if counts.get("source", 0) == 0:
        reasoning.append("No source files changed — security/logic findings unlikely but agents still run for safety.")
    if counts.get("test", 0) == 0 and counts.get("source", 0) > 0:
        reasoning.append("Source changed with no test changes — flag to test coverage agent as high priority.")
    if not reasoning:
        reasoning.append("Standard PR: running all five specialist agents in parallel.")
    return {"orchestrator_plan": reasoning, "specialists_run": ["security", "static_analysis", "logic", "test_coverage", "documentation"]}


def finalize(state: Dict[str, Any]) -> Dict[str, Any]:
    decision = state["decision"]
    if decision == "BLOCK":
        merge_policy = "Merge blocked. Requires human security sign-off before this PR can proceed."
    elif decision == "REQUEST_CHANGES":
        merge_policy = "Merge blocked until major findings are addressed by the author."
    elif decision == "APPROVE_WITH_COMMENTS":
        merge_policy = "Mergeable. Minor findings left as follow-up comments, not blocking."
    else:
        merge_policy = "Mergeable. No blocking issues found."
    return {"merge_policy": merge_policy}
