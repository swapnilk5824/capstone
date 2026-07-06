"""
Acceptance-criteria tests, one per required scenario. Run with:
    python -m pytest tests/ -v
All run in CODEGUARD_MODE=mock (default) so they need no API key
and are fully deterministic.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("CODEGUARD_MODE", "mock")

from src.pipeline import run_review


def test_clean_pr_is_approved():
    result = run_review("sample_data/pr_clean/pr.json", verbose=False)
    assert result["decision"] == "APPROVE"
    assert result["all_findings"] == []


def test_hardcoded_secret_blocks_merge():
    result = run_review("sample_data/pr_security/pr.json", verbose=False)
    assert result["decision"] == "BLOCK"
    categories = {f["category"] for f in result["all_findings"]}
    assert "security" in categories
    severities = {f["severity"] for f in result["all_findings"]}
    assert "blocker" in severities


def test_missing_tests_requests_changes():
    result = run_review("sample_data/pr_missing_tests/pr.json", verbose=False)
    assert result["decision"] == "REQUEST_CHANGES"
    categories = {f["category"] for f in result["all_findings"]}
    assert "testing" in categories


def test_style_only_is_approved_with_comments():
    result = run_review("sample_data/pr_style/pr.json", verbose=False)
    assert result["decision"] == "APPROVE_WITH_COMMENTS"
    severities = {f["severity"] for f in result["all_findings"]}
    assert "blocker" not in severities
    assert "major" not in severities


def test_all_eight_agents_contribute_to_state():
    result = run_review("sample_data/pr_clean/pr.json", verbose=False)
    expected_keys = [
        "pr", "orchestrator_plan", "security_findings", "style_findings",
        "logic_findings", "test_findings", "docs_findings",
        "all_findings", "decision", "merge_policy",
    ]
    for k in expected_keys:
        assert k in result, f"missing state key: {k}"
