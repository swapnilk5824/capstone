"""
Reporter / Aggregator Agent

Role: last node before the orchestrator's final decision. Merges
findings from all specialist agents, deduplicates, sorts by
severity, and renders a human-readable Markdown review report.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..core.types import Finding, SEVERITY_ORDER

SYSTEM_PROMPT = """You are the Reporter Agent in a multi-agent code review system.
You receive structured findings from five specialist agents (security, static
analysis, logic, test coverage, documentation). Merge them, remove near-duplicate
findings on the same file/line/category, sort by severity (blocker > major > minor
> info), and produce a concise Markdown review report a human engineer can act on
in under two minutes."""


def _collect_findings(state: Dict[str, Any]) -> List[Finding]:
    keys = ["security_findings", "style_findings", "logic_findings", "test_findings", "docs_findings"]
    all_findings: List[Finding] = []
    for k in keys:
        all_findings.extend(state.get(k, []))
    all_findings.sort(key=lambda f: SEVERITY_ORDER.get(f.severity, 9))
    return all_findings


def _render_report(pr: Dict[str, Any], findings: List[Finding], decision: str) -> str:
    lines = [f"# Code Review Report: {pr['title']}", ""]
    lines.append(f"**Decision: {decision}**")
    lines.append("")
    counts = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    summary = ", ".join(f"{v} {k}" for k, v in sorted(counts.items(), key=lambda kv: SEVERITY_ORDER.get(kv[0], 9))) or "no issues found"
    lines.append(f"**Summary:** {summary}")
    lines.append("")
    if not findings:
        lines.append("No issues found across security, style, logic, test coverage, or documentation checks.")
    else:
        for f in findings:
            loc = f"{f.file}:{f.line}" if f.line else f.file
            lines.append(f"- **[{f.severity.upper()}][{f.category}]** `{loc}` — {f.message}")
            if f.suggestion:
                lines.append(f"  - *Suggestion:* {f.suggestion}")
    return "\n".join(lines)


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    findings = _collect_findings(state)
    has_blocker = any(f.severity == "blocker" for f in findings)
    has_major = any(f.severity == "major" for f in findings)

    if has_blocker:
        decision = "BLOCK"
    elif has_major:
        decision = "REQUEST_CHANGES"
    elif findings:
        decision = "APPROVE_WITH_COMMENTS"
    else:
        decision = "APPROVE"

    report_md = _render_report(state["pr"], findings, decision)
    return {
        "all_findings": [f.to_dict() for f in findings],
        "decision": decision,
        "report_markdown": report_md,
    }
