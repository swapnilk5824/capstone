"""
Documentation Agent

Role: checks that new public functions/classes have docstrings and
that README/docs are updated when public API surface changes.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from ..core.types import Finding
from ..core.agent_helpers import run_specialist, build_diff_prompt

SYSTEM_PROMPT = """You are the Documentation Agent in a multi-agent code review system.
Flag new public functions/classes (not starting with underscore) added in the
diff that have no docstring on the following line. Severity 'minor'. Do not
flag private/internal helpers (leading underscore) or test functions."""

NEW_DEF = re.compile(r"^\+\s*def\s+([a-zA-Z][a-zA-Z0-9_]*)\s*\(")
NEW_CLASS = re.compile(r"^\+\s*class\s+([A-Za-z][A-Za-z0-9_]*)")


def _mock_analyze(state: Dict[str, Any]) -> List[Finding]:
    findings: List[Finding] = []
    for f in state["pr"]["files"]:
        if f["classification"] != "source":
            continue
        lines = f["diff"].splitlines()
        for i, line in enumerate(lines):
            m = NEW_DEF.match(line) or NEW_CLASS.match(line)
            if not m:
                continue
            name = m.group(1)
            if name.startswith("_"):
                continue
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            has_docstring = '"""' in next_line or "'''" in next_line
            if not has_docstring:
                findings.append(
                    Finding(
                        file=f["path"],
                        line=i + 1,
                        severity="minor",
                        category="docs",
                        message=f"Public '{name}' has no docstring",
                        suggestion="Add a one-line docstring describing purpose, args, and return value.",
                        agent="documentation_agent",
                    )
                )
    return findings


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    user_prompt = build_diff_prompt(state["pr"], lambda f: f["classification"] == "source")
    findings = run_specialist("documentation_agent", state, SYSTEM_PROMPT, user_prompt, _mock_analyze)
    return {"docs_findings": findings}
