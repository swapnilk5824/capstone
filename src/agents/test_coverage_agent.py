"""
Test Coverage Agent

Role: checks whether source changes are accompanied by test changes.
Does not run the test suite (no execution sandbox for the PR's repo
in this capstone) — instead reasons over which source files changed
and whether a corresponding test file changed, which is a reasonable
static proxy for coverage in a review-gate context.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..core.types import Finding
from ..core.agent_helpers import run_specialist, build_diff_prompt

SYSTEM_PROMPT = """You are the Test Coverage Agent in a multi-agent code review system.
Given the list of changed source files and changed test files, flag any source
file that adds new functions/logic but has no corresponding test file touched
in this PR. Severity 'major' if the PR has zero test changes despite non-trivial
source changes; 'minor' if some but possibly incomplete test coverage."""


def _mock_analyze(state: Dict[str, Any]) -> List[Finding]:
    pr = state["pr"]
    findings: List[Finding] = []
    source_files = [f for f in pr["files"] if f["classification"] == "source"]
    test_files = [f for f in pr["files"] if f["classification"] == "test"]

    if source_files and not test_files:
        for f in source_files:
            added_lines = [l for l in f["diff"].splitlines() if l.startswith("+") and not l.startswith("+++")]
            if len(added_lines) >= 3:  # non-trivial change
                findings.append(
                    Finding(
                        file=f["path"],
                        severity="major",
                        category="testing",
                        message="Source file has non-trivial changes but no test file was added or updated in this PR",
                        suggestion="Add or update unit tests covering the new/changed behavior.",
                        agent="test_coverage_agent",
                    )
                )
    return findings


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    user_prompt = build_diff_prompt(state["pr"], lambda f: f["classification"] in ("source", "test"))
    findings = run_specialist("test_coverage_agent", state, SYSTEM_PROMPT, user_prompt, _mock_analyze)
    return {"test_findings": findings}
