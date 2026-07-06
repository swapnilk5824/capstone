# CodeGuard — Multi-Agent Code Review Swarm

A capstone multi-agent system that reviews a pull request the way a small
engineering team would: a security specialist, a style checker, a logic
reviewer, a test-coverage checker, and a docs checker each look at the diff
independently and in parallel, and a reporter + orchestrator turn their
findings into one decision — `APPROVE`, `APPROVE_WITH_COMMENTS`,
`REQUEST_CHANGES`, or `BLOCK`.

8 agents total. See `docs/ARCHITECTURE.md` for the full design writeup and
diagram.

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the built-in demo scenarios (no API key needed — deterministic mock mode)
python3 main.py review sample_data/pr_clean/pr.json
python3 main.py review sample_data/pr_security/pr.json
python3 main.py review sample_data/pr_missing_tests/pr.json
python3 main.py review sample_data/pr_style/pr.json

# 3. Run the acceptance test suite
python3 -m pytest tests/ -v
```

Expected decisions: `pr_clean` → APPROVE, `pr_security` → BLOCK,
`pr_missing_tests` → REQUEST_CHANGES, `pr_style` → APPROVE_WITH_COMMENTS.
Full transcripts are saved in `docs/sample_io/`.

### Running with real Claude calls (live mode)

By default the system runs in `CODEGUARD_MODE=mock`, which uses
deterministic rule-based analyzers standing in for each agent's LLM call —
this keeps the deliverable reproducible and free to run for grading. To
have the five specialist agents actually call Claude:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export CODEGUARD_MODE=live
python3 main.py review sample_data/pr_security/pr.json
```

In live mode, each specialist agent sends its system prompt (see
`.claude/AGENT_PROMPTS.md`) plus the diff to Claude with the shared
`flag_finding` tool schema (`src/tools/tool_schemas.py`); `tool_use` blocks
in the response become structured `Finding` objects, same as mock mode, so
the reporter/orchestrator logic downstream is identical either way.

### Reviewing your own PR

Build a `pr.json` bundle with this shape and point the CLI at it:

```json
{
  "title": "Short PR title",
  "description": "What and why",
  "files": [
    {"path": "src/foo.py", "status": "modified", "diff": "+def foo():\n+    ...\n"}
  ]
}
```

```bash
python3 main.py review path/to/pr.json          # Markdown report
python3 main.py review path/to/pr.json --json    # raw structured result
```

## Project layout

```
codeguard/
├── main.py                      CLI entrypoint
├── requirements.txt
├── src/
│   ├── pipeline.py               Builds & runs the 8-agent graph
│   ├── core/
│   │   ├── graph.py               Lightweight LangGraph-style state-graph engine
│   │   ├── llm_client.py          Anthropic API client + mock client
│   │   ├── agent_helpers.py       Shared live/mock runner for specialist agents
│   │   └── types.py               Finding dataclass, severity ordering
│   ├── tools/
│   │   └── tool_schemas.py        flag_finding / read_file / search_code tool schemas
│   └── agents/
│       ├── ingestion_agent.py     Parses & classifies PR files
│       ├── orchestrator_agent.py  Routing plan + final merge policy
│       ├── security_agent.py      Secrets, injection, unsafe eval/exec, weak crypto
│       ├── static_analysis_agent.py  Style/convention checks
│       ├── logic_agent.py         Correctness heuristics
│       ├── test_coverage_agent.py Source-vs-test change coverage proxy
│       ├── documentation_agent.py Missing docstrings on public functions
│       └── reporter_agent.py      Merges findings, renders report, sets decision
├── sample_data/
│   ├── pr_clean/pr.json           Scenario 1: clean PR, tests included
│   ├── pr_security/pr.json        Scenario 2: hardcoded secret + shell=True
│   ├── pr_missing_tests/pr.json   Scenario 3: source change, zero tests
│   └── pr_style/pr.json           Scenario 4: style-only issues
├── tests/
│   └── test_acceptance.py         One test per acceptance-criterion scenario
├── docs/
│   ├── ARCHITECTURE.md            Design notes + Mermaid diagram
│   ├── cowork_notes.md            How this was built / how to use it with Cowork
│   └── sample_io/                 Saved input/output for every scenario
└── .claude/
    ├── settings.json              Claude Code permissions/config for this repo
    └── AGENT_PROMPTS.md           All 8 system prompts collected in one place
```

## Design notes (summary)

- **Why 8 agents, not 1 big prompt:** each specialist has a narrow,
  explicitly-scoped system prompt ("flag X, do NOT flag Y") so responsibility
  boundaries are crisp and agents don't step on each other's findings. See
  `docs/ARCHITECTURE.md` for the full rationale.
- **Why parallel fan-out:** the five specialists only read shared PR state
  and each write to their own state key, so there's no race condition
  running them concurrently — implemented with a `ThreadPoolExecutor` in
  `src/core/graph.py`.
- **Why a custom graph engine instead of installing LangGraph:**
  documented as a deliberate tradeoff in `docs/ARCHITECTURE.md` — same
  node/edge/shared-state model, zero install risk for a graded deliverable,
  mechanical migration path to native LangGraph if this goes to production.
- **Why mock mode exists:** lets the entire 8-agent pipeline run
  deterministically and be unit-tested without API credentials or network
  access, while the exact same code path supports live Claude calls when
  `ANTHROPIC_API_KEY` is set.

## Acceptance criteria → test mapping

| Scenario | Fixture | Expected decision | Test |
|---|---|---|---|
| Clean PR with tests | `sample_data/pr_clean/pr.json` | `APPROVE` | `test_clean_pr_is_approved` |
| Hardcoded secret + shell injection risk | `sample_data/pr_security/pr.json` | `BLOCK` | `test_hardcoded_secret_blocks_merge` |
| Source change with no tests | `sample_data/pr_missing_tests/pr.json` | `REQUEST_CHANGES` | `test_missing_tests_requests_changes` |
| Style-only issues (naming, print, missing docstring) | `sample_data/pr_style/pr.json` | `APPROVE_WITH_COMMENTS` | `test_style_only_is_approved_with_comments` |
| All 8 agents contribute to shared state | any fixture | all expected state keys present | `test_all_eight_agents_contribute_to_state` |

Run `python3 -m pytest tests/ -v` to verify all five pass.
