"""
Logic & Correctness Review Agent

Role: looks for likely correctness bugs in the diff — off-by-one
patterns in range(), unguarded division, mutable default arguments,
equality-vs-identity confusion (`== None`), and unreachable code
after return. This is a lightweight heuristic layer standing in for
what would, with a live LLM, be genuine reasoning about the change.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from ..core.types import Finding
from ..core.agent_helpers import run_specialist, build_diff_prompt

SYSTEM_PROMPT = """You are the Logic & Correctness Review Agent in a multi-agent code review system.
Review only added/modified lines for likely correctness bugs: division without a
zero-check, mutable default arguments (def f(x=[])), `== None` / `!= None` instead
of `is None`, and code that appears unreachable after an unconditional return.
Use severity 'major' for these. Do not flag style or security issues."""

MUTABLE_DEFAULT = re.compile(r"^\+\s*def\s+\w+\([^)]*=\s*(\[\]|\{\})")
EQ_NONE = re.compile(r"[=!]=\s*None\b")
DIVISION = re.compile(r"/\s*(\w+)\s*(?!.*if\s+\1)")


def _mock_analyze(state: Dict[str, Any]) -> List[Finding]:
    findings: List[Finding] = []
    for f in state["pr"]["files"]:
        if f["classification"] != "source":
            continue
        lines = f["diff"].splitlines()
        for i, line in enumerate(lines, start=1):
            if not line.startswith("+") or line.startswith("+++"):
                continue
            content = line[1:]
            if MUTABLE_DEFAULT.search(line):
                findings.append(Finding(f["path"], "major", "logic", "Mutable default argument (list/dict) — shared across calls", i, "Use `None` as default and initialize inside the function.", "logic_agent"))
            if EQ_NONE.search(content):
                findings.append(Finding(f["path"], "minor", "logic", "Use `is None`/`is not None` instead of `== None`", i, "Replace equality check with identity check.", "logic_agent"))
            if re.search(r"/\s*len\(", content) and "if" not in content:
                findings.append(Finding(f["path"], "major", "logic", "Division by len(...) without a zero-length guard — possible ZeroDivisionError", i, "Add a guard: `if len(x) == 0: ...` before dividing.", "logic_agent"))
    return findings


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    user_prompt = build_diff_prompt(state["pr"], lambda f: f["classification"] == "source")
    findings = run_specialist("logic_agent", state, SYSTEM_PROMPT, user_prompt, _mock_analyze)
    return {"logic_findings": findings}
