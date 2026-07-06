"""
Security Review Agent

Role: scans added/modified lines for hardcoded secrets, unsafe
dynamic execution (eval/exec), disabled TLS/cert verification,
shell injection risk, and use of weak crypto. Runs in parallel with
the other specialist agents.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from ..core.types import Finding
from ..core.agent_helpers import run_specialist, build_diff_prompt

SYSTEM_PROMPT = """You are the Security Review Agent in a multi-agent code review system.
Review only the provided diff hunks (added/modified lines, marked with '+').
Flag: hardcoded secrets/API keys/passwords, use of eval/exec on untrusted input,
disabled TLS/certificate verification, SQL string concatenation (injection risk),
shell=True with unsanitized input, and weak/broken crypto (md5/sha1 for passwords).
Call flag_finding once per distinct issue with severity 'blocker' for anything
directly exploitable, 'major' otherwise. Do not flag style issues."""

SECRET_PATTERNS = [
    (re.compile(r"""(?i)\w*(api[_-]?key|secret|password|passwd|token)\w*\s*=\s*['"][^'"]{6,}['"]"""), "Hardcoded credential/secret found"),
    (re.compile(r"\beval\("), "Use of eval() on potentially untrusted input"),
    (re.compile(r"\bexec\("), "Use of exec() on potentially untrusted input"),
    (re.compile(r"verify\s*=\s*False"), "TLS/certificate verification disabled"),
    (re.compile(r"shell\s*=\s*True"), "subprocess call with shell=True (injection risk if input is unsanitized)"),
    (re.compile(r"\bmd5\("), "Use of MD5 (weak hash) — avoid for security-sensitive purposes"),
    (re.compile(r"""SELECT .* \+ |f["']SELECT|%s["']\s*%|f["']DELETE|f["']INSERT""", re.IGNORECASE), "Possible SQL built via string concatenation/formatting — injection risk"),
]


def _mock_analyze(state: Dict[str, Any]) -> List[Finding]:
    findings: List[Finding] = []
    for f in state["pr"]["files"]:
        if f["classification"] not in ("source", "config"):
            continue
        added_lines = [l for l in f["diff"].splitlines() if l.startswith("+") and not l.startswith("+++")]
        for i, line in enumerate(added_lines, start=1):
            for pattern, msg in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        Finding(
                            file=f["path"],
                            line=i,
                            severity="blocker",
                            category="security",
                            message=msg,
                            suggestion="Move secrets to environment variables/secret manager; avoid eval/exec on external input; use parameterized queries.",
                            agent="security_agent",
                        )
                    )
    return findings


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    user_prompt = build_diff_prompt(state["pr"], lambda f: f["classification"] in ("source", "config"))
    findings = run_specialist("security_agent", state, SYSTEM_PROMPT, user_prompt, _mock_analyze)
    return {"security_findings": findings}
