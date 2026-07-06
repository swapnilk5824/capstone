"""
Builds and exposes the CodeGuard review graph:

  ingestion -> orchestrator.plan -> [security, static_analysis, logic,
  test_coverage, documentation] (parallel) -> reporter -> orchestrator.finalize

8 distinct agents total: ingestion, orchestrator (2 nodes), security,
static_analysis, logic, test_coverage, documentation, reporter.
"""
from __future__ import annotations

from typing import Any, Dict

from .core.graph import StateGraph
from .agents import (
    ingestion_agent,
    orchestrator_agent,
    security_agent,
    static_analysis_agent,
    logic_agent,
    test_coverage_agent,
    documentation_agent,
    reporter_agent,
)


def build_graph() -> StateGraph:
    g = StateGraph("codeguard_review")
    g.add_node("ingestion", ingestion_agent.run)
    g.add_node("orchestrator_plan", orchestrator_agent.plan)
    g.add_node("security", security_agent.run)
    g.add_node("static_analysis", static_analysis_agent.run)
    g.add_node("logic", logic_agent.run)
    g.add_node("test_coverage", test_coverage_agent.run)
    g.add_node("documentation", documentation_agent.run)
    g.add_node("reporter", reporter_agent.run)
    g.add_node("orchestrator_finalize", orchestrator_agent.finalize)

    g.add_step("ingestion")
    g.add_step("orchestrator_plan")
    g.add_parallel(["security", "static_analysis", "logic", "test_coverage", "documentation"])
    g.add_step("reporter")
    g.add_step("orchestrator_finalize")
    return g


def run_review(pr_bundle_path: str, verbose: bool = True) -> Dict[str, Any]:
    graph = build_graph()
    initial_state = {"pr_bundle_path": pr_bundle_path}
    return graph.run(initial_state, verbose=verbose)
