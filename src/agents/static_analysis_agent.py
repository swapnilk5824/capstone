"""
Static Analysis Agent

Role: style and convention checks — line length, naming conventions,
unused-looking imports, bare except clauses, print() left in library
code. Complements (does not duplicate) the Logic agent, which looks
at correctness rather than style.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from ..core.types import Finding
from ..core.agent_helpers import run_specialist, build_diff_prompt

SYSTEM_PROMPT = """You are the Static Analysis Agent in a multi-agent code review system.
Review only added/modified lines in the diff for style and convention issues:
lines over 100 chars, bare `except:` clauses, leftover print()/console.log debugging
statements, non-snake_case function names in Python. These are 'minor' severity
unless a bare except swallows exceptions silently in a way that could hide bugs,
in which case use 'major'. Do not flag security or logic issues."""

BARE_EXCEPT = re.compile(r"^\s*except\s*:\s*$")
PRINT_DEBUG = re.compile(r"^\+\s*(print\(|console\.log\()")
BAD_FN_NAME = re.compile(r"^\+\s*def\s+([A-Z][A-Za-z0-9]*)\s*\(")


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
            if len(content) > 100:
                findings.append(Finding(f["path"], "minor", "style", f"Line exceeds 100 characters ({len(content)})", i, "Wrap or shorten the line.", "static_analysis_agent"))
            if BARE_EXCEPT.match(content):
                findings.append(Finding(f["path"], "major", "style", "Bare 'except:' clause swallows all exceptions", i, "Catch specific exception types.", "static_analysis_agent"))
            if PRINT_DEBUG.match(line):
                findings.append(Finding(f["path"], "minor", "style", "Debug print/console.log left in code", i, "Remove or replace with proper logging.", "static_analysis_agent"))
            m = BAD_FN_NAME.match(line)
            if m:
                findings.append(Finding(f["path"], "minor", "style", f"Function name '{m.group(1)}' should be snake_case", i, "Rename to snake_case per PEP8.", "static_analysis_agent"))
    return findings


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    user_prompt = build_diff_prompt(state["pr"], lambda f: f["classification"] == "source")
    findings = run_specialist("static_analysis_agent", state, SYSTEM_PROMPT, user_prompt, _mock_analyze)
    return {"style_findings": findings}
