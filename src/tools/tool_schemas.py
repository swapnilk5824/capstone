"""
Tool schemas (Anthropic Messages API `tools` format) shared by the
review agents when running in CODEGUARD_MODE=live. Each specialist
agent exposes a `flag_finding` tool so the model returns structured
findings instead of free text, and a `read_file` tool so it can pull
full file context beyond the diff hunk if needed.
"""

FLAG_FINDING_TOOL = {
    "name": "flag_finding",
    "description": (
        "Record one review finding for the current file/diff. Call this "
        "once per distinct issue found. If there are no issues, do not call it."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "file": {"type": "string", "description": "File path the finding applies to"},
            "line": {"type": "integer", "description": "Approximate line number in the diff, if known"},
            "severity": {
                "type": "string",
                "enum": ["blocker", "major", "minor", "info"],
                "description": "blocker = must fix before merge, major = should fix, minor = nice to fix, info = FYI",
            },
            "category": {"type": "string", "description": "e.g. security, style, logic, testing, docs"},
            "message": {"type": "string", "description": "Human-readable description of the issue"},
            "suggestion": {"type": "string", "description": "Optional concrete fix suggestion"},
        },
        "required": ["file", "severity", "category", "message"],
    },
}

READ_FILE_TOOL = {
    "name": "read_file",
    "description": "Read the full current contents of a file in the PR, beyond just the diff hunk.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Repo-relative file path"},
        },
        "required": ["path"],
    },
}

SEARCH_CODE_TOOL = {
    "name": "search_code",
    "description": "Search the changed files for a regex pattern (e.g. to find related usages).",
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern to search for"},
        },
        "required": ["pattern"],
    },
}

ALL_REVIEW_TOOLS = [FLAG_FINDING_TOOL, READ_FILE_TOOL, SEARCH_CODE_TOOL]
