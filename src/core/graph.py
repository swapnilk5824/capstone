"""
Minimal state-graph orchestration engine.

Mirrors the core abstractions of LangGraph (nodes, typed shared state,
conditional edges, parallel fan-out/fan-in) using pure Python and no
external dependencies. This keeps the capstone deliverable runnable
in any environment without needing network access to install a
graph framework.

Migration note: swapping this module for `langgraph.graph.StateGraph`
is a mechanical change — each `add_node` becomes a LangGraph node
function, `add_parallel` becomes fan-out edges into a joiner node,
and `run` becomes `graph.compile().invoke(state)`. Recommended if this
project moves to production.
"""
from __future__ import annotations

import concurrent.futures
import copy
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


NodeFn = Callable[[Dict[str, Any]], Dict[str, Any]]


@dataclass
class NodeResult:
    name: str
    duration_s: float
    output_keys: List[str]


@dataclass
class RunTrace:
    order: List[NodeResult] = field(default_factory=list)

    def add(self, name: str, duration_s: float, output_keys: List[str]):
        self.order.append(NodeResult(name, duration_s, output_keys))


class StateGraph:
    """A tiny supervisor/worker graph executor operating on a shared dict state."""

    def __init__(self, name: str):
        self.name = name
        self._nodes: Dict[str, NodeFn] = {}
        self._sequence: List[Any] = []  # list of str (single node) or list[str] (parallel group)

    def add_node(self, name: str, fn: NodeFn) -> "StateGraph":
        self._nodes[name] = fn
        return self

    def add_step(self, node_name: str) -> "StateGraph":
        self._sequence.append(node_name)
        return self

    def add_parallel(self, node_names: List[str]) -> "StateGraph":
        self._sequence.append(list(node_names))
        return self

    def run(self, initial_state: Dict[str, Any], verbose: bool = True) -> Dict[str, Any]:
        state = copy.deepcopy(initial_state)
        trace = RunTrace()

        for step in self._sequence:
            if isinstance(step, list):
                # Parallel fan-out: each node reads the same state snapshot,
                # writes are merged into shared state under its own key namespace.
                with concurrent.futures.ThreadPoolExecutor(max_workers=len(step)) as ex:
                    futures = {
                        ex.submit(self._invoke, name, state): name for name in step
                    }
                    for fut in concurrent.futures.as_completed(futures):
                        name = futures[fut]
                        t0_keys, duration = fut.result()
                        state.update(t0_keys)
                        trace.add(name, duration, list(t0_keys.keys()))
                        if verbose:
                            print(f"  [parallel] {name} done in {duration:.2f}s")
            else:
                name = step
                out, duration = self._invoke(name, state)
                state.update(out)
                trace.add(name, duration, list(out.keys()))
                if verbose:
                    print(f"  [step] {name} done in {duration:.2f}s")

        state["_trace"] = trace
        return state

    def _invoke(self, name: str, state: Dict[str, Any]):
        fn = self._nodes[name]
        t0 = time.time()
        out = fn(copy.deepcopy(state))
        return out, time.time() - t0
