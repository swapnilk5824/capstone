# Claude Cowork Usage Notes

## How this capstone was built
This repository was built in a single Claude session using the computer/file
tools (equivalent to what Claude Cowork exposes for non-developers): a
sandboxed Linux workspace with bash, file read/write, and a Python
interpreter. The workflow mirrored what a Cowork session would do end to
end:

1. **Scaffold** — created the directory layout (`src/agents`, `src/core`,
   `src/tools`, `sample_data`, `tests`, `.claude`, `docs`).
2. **Author each agent as its own file** with an explicit `SYSTEM_PROMPT`
   constant, a tool-schema contract, and a deterministic mock fallback so
   the pipeline is independently runnable without live API credentials.
3. **Wire the graph** (`src/pipeline.py`) connecting ingestion → orchestrator
   planning → five parallel specialists → reporter → orchestrator
   finalization.
4. **Generate four sample PR fixtures** (clean, security issue, missing
   tests, style-only) designed to each exercise a different final
   decision path.
5. **Run the pipeline against all four fixtures directly in the sandbox**
   (`python3 main.py review sample_data/<case>/pr.json`), inspect the
   output, and iterate on the detection regexes when a fixture didn't
   trigger the intended finding (e.g. the `AWS_SECRET_KEY` pattern initially
   slipped past the secret-detection regex — caught by actually running it,
   not by inspection).
6. **Write and run an automated acceptance test suite** (`pytest tests/`)
   that pins the four scenario decisions down as regression tests.
7. **Write the README, architecture diagram, and this notes file** from the
   working, tested code rather than from a plan — every command shown in
   the README was actually executed in the build session.

## Recommended Cowork workflow for *using* CodeGuard going forward
If a team adopts this project via Claude Cowork for day-to-day PR review:

1. Drop a new `pr.json` bundle (or a script that exports one from a real
   GitHub PR diff via `gh pr diff`) into `sample_data/` or a scratch folder.
2. Ask Cowork: *"Run CodeGuard on this PR bundle and summarize the
   blocking issues."* Cowork runs `python3 main.py review <path>` in its
   sandbox and reads back the Markdown report.
3. For live-mode runs (`CODEGUARD_MODE=live`), Cowork should be given the
   `ANTHROPIC_API_KEY` as an environment secret, never pasted into chat or
   committed to the repo.
4. Because each specialist agent is a separate, small Python module,
   Cowork (or Claude Code) can be asked to add a new specialist — e.g. a
   "dependency licensing agent" — by copying the shape of
   `src/agents/documentation_agent.py` and adding one line to
   `src/pipeline.py`.

## Transcript / screenshot placeholder
This deliverable was produced in a single non-interactive build session;
no separate Cowork screen-recording was captured. The full command history
executed during the build (scaffolding, four review runs, pytest run,
regex fix) is reproducible verbatim from the commands listed in the
README's "Reproduce the build" section, and stdout for each is included
inline in `docs/sample_io/`.
