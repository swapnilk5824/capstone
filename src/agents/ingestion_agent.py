"""
Diff Ingestion Agent

Role: first node in the graph. Loads the raw PR bundle (title,
description, per-file diffs/content), classifies each file
(source / test / docs / config), and produces a normalized `pr`
object that every downstream specialist agent consumes. This keeps
each specialist agent free of parsing logic.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

SYSTEM_PROMPT = """You are the Ingestion Agent in a multi-agent code review system.
Your only job is to parse the incoming pull request bundle and classify each
changed file as one of: source, test, docs, config. You do not evaluate code
quality — that is other agents' job. Output strict JSON only."""


def _classify(path: str) -> str:
    lower = path.lower()
    if "test" in lower or lower.startswith("tests/") or "/tests/" in lower or lower.endswith("_test.py") or lower.endswith(".test.js"):
        return "test"
    if lower.endswith((".md", ".rst", ".txt")) or "docs/" in lower or lower == "readme.md":
        return "docs"
    if lower.endswith((".yml", ".yaml", ".json", ".toml", ".ini", ".cfg")) or "config" in lower:
        return "config"
    return "source"


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    pr_path = state["pr_bundle_path"]
    with open(pr_path, "r") as f:
        bundle = json.load(f)

    files: List[Dict[str, Any]] = bundle["files"]
    for f in files:
        f["classification"] = _classify(f["path"])

    counts: Dict[str, int] = {}
    for f in files:
        counts[f["classification"]] = counts.get(f["classification"], 0) + 1

    pr = {
        "title": bundle.get("title", ""),
        "description": bundle.get("description", ""),
        "files": files,
        "file_counts": counts,
        "has_test_changes": counts.get("test", 0) > 0,
        "has_source_changes": counts.get("source", 0) > 0,
    }
    return {"pr": pr}
