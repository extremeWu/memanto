"""
MEMANTO CLI - Connect Templates

Per-agent instruction content and skill templates for MEMANTO integration.
"""


# Shared MEMANTO Sentinel markers

MEMANTO_SENTINEL = "<!-- MEMANTO-MANAGED-SECTION -->"
MEMANTO_SENTINEL_END = "<!-- /MEMANTO-MANAGED-SECTION -->"


# Shared SKILL.md content (same across all agents)

SKILL_MD_CONTENT = """---
name: memanto-memory
description: Use this skill when you need to store or search MEMANTO persistent memories. It defines mandatory guidelines for best practices, memory types, confidence levels, tagging, and patterns for effective agent memory usage.
---

# MEMANTO Memory Skill

Detailed reference for using MEMANTO persistent memory effectively.

## Memory Types: Decision Matrix

| Type | When to Use | Confidence | Example |
|------|-------------|------------|---------|
| `fact` | Verified information, project status | 0.9-1.0 | "MEMANTO uses PostgreSQL for metadata" |
| `decision` | Architecture choices, approach selections | 0.9-1.0 | "Chose React over Vue for frontend" |
| `instruction` | Standing rules, preferences, guidelines | 0.9-1.0 | "Always use type hints in Python" |
| `commitment` | Promises, TODOs, obligations | 1.0 | "Will deploy monitoring by Friday" |
| `preference` | User/team preferences | 0.8-1.0 | "User prefers dark mode" |
| `goal` | Objectives, targets, milestones | 0.8-1.0 | "Launch CLI by end of March" |
| `artifact` | Tool outputs, reports, file locations | 0.9-1.0 | "Report saved at ./reports/q1.md" |
| `learning` | Knowledge acquired from experience | 0.7-0.9 | "Batch operations 100x faster" |
| `event` | Important conversations, milestones | 0.8-0.95 | "Completed Phase 1 features" |
| `relationship` | Team context, collaboration patterns | 0.85-0.95 | "Alice is lead backend engineer" |
| `observation` | Patterns noticed, behaviors | 0.6-0.85 | "User prefers short responses" |
| `error` | Failures, bugs, lessons learned | 0.95-1.0 | "Namespace format bug - use underscores" |
| `context` | Session summaries, status updates | 0.9-1.0 | "Project 70% done, API complete" |

## Confidence Levels

- **1.0** — Explicit user statement, verified fact, standing instruction
- **0.9-0.95** — Strong consensus, well-tested approach, clear team preference
- **0.8-0.85** — Observed pattern (3+ times), indirect but supported preference
- **0.7-0.75** — Emerging pattern (2 times), reasonable inference
- **0.6-0.65** — Single observation, uncertain interpretation
- **< 0.6** — Don't store. Too uncertain.

## Provenance Types

Always categorize the source of the memory. Valid options:
- `explicit_statement` — Directly stated by user
- `inferred` — Derived from behavior/context
- `observed` — Seen in action
- `corrected` — Updated after contradiction
- `validated` — Confirmed/verified

## Source Types

Always specify the tool or agent creating the memory.
- For AI agents: Use the agent name (e.g., `--source claude_code` or `--source cursor`)
- Valid base sources (if not using specific agent name): `user`, `agent`, `tool`, `system`

## Tagging Best Practices

Use 2-5 tags per memory. Tags make memories findable.

Good: `--tags "authentication,oauth,security"`
Good: `--tags "bug-fix,namespace,commit-3f39351"`
Bad: `--tags "important"` (too generic)
Bad: `--tags "thing"` (not descriptive)

Conventions:
- Lowercase with hyphens: `bug-fix` not `BugFix`
- Be specific: `authentication-oauth` not `auth`
- Include refs: `commit-abc123` for git references

## Patterns

### Session Start
```bash
memanto recall "instructions decisions goals" --limit 20
memanto answer "What are my pending commitments?"
```

### After Important Work
```bash
memanto remember "Implemented X using approach Y because Z. Commit abc123." --type decision --tags "feature-x" --confidence 0.95 --provenance "inferred" --source "claude_code"
memanto remember "Learned that batch ops reduce API calls 100x." --type learning --tags "performance" --confidence 0.85 --provenance "observed" --source "claude_code"
```

### When User Corrects You
```bash
memanto remember "User corrected: prefer pytest over unittest." --type learning --tags "correction,testing" --confidence 1.0 --provenance "corrected" --source "claude_code"
```

### Before Answering Uncertain Questions
```bash
memanto recall "topic of the question"
memanto answer "What did we decide about X?"
```

## Pitfalls to Avoid

1. **Memory hoarding** — Ask "Will this matter in a week?" before storing
2. **Vague content** — Bad: "better performance" → Good: "API response < 200ms"
3. **No context** — Bad: "fixed bug" → Good: "Fixed OAuth expiry bug. Commit abc123."
4. **Duplicates** — Search first (`memanto recall`), then store if not found
5. **Missing tags** — Always include tags for retrieval

## Command Reference

```bash
# Store memory
memanto remember "content" --type TYPE --tags "tag1,tag2" --confidence 0.9 --provenance "inferred" --source "claude_code"

# Search memories
memanto recall "query" --limit 10 --type TYPE --min-confidence 0.8

# Ask questions (RAG)
memanto answer "question"

# Sync memories to project
memanto memory sync --project-dir .
```
"""


# Per-agent instruction content


def _base_instruction_content(
    tool_phrase: str = "the terminal", note_suffix: str = ""
) -> str:
    """Generate base MEMANTO instruction content, adapted per agent."""
    note_line = ""
    if note_suffix:
        note_line = f"\n> **Note**: {note_suffix}"

    return f"""{MEMANTO_SENTINEL}
## MEMANTO Memory Integration

This project is connected to **MEMANTO** — a persistent memory system.
`MEMORY.md` is auto-synced at session start with the agent's full memory.

> **CRITICAL**: All `memanto` commands are **shell commands**. Always run them using {tool_phrase}.

### MANDATORY: Read MEMORY.md First

**Before doing ANY work**, read `MEMORY.md` in the project root. It contains
the user's preferences, facts, goals, instructions, decisions, and commitments
from all previous sessions. You MUST follow any instructions and preferences found there.

### MANDATORY: Search Memory Before Giving Up

When the user asks a question you are unsure about, or asks about past context,
decisions, or preferences, you MUST search memory first before saying you don't know.
Run in {tool_phrase}:
- `memanto recall "query"` — search by semantic similarity
- `memanto answer "question"` — RAG-powered answers grounded in memory

Do NOT say "I don't have context on that" without running these commands first.

### MANDATORY: Store Memories Proactively

You MUST run `memanto remember` to store important information discovered
during this session. Specifically, store:

- **User preferences** they mention (coding style, naming conventions, tools they like/dislike)
- **Decisions made** during this session (architecture choices, library selections, approaches taken)
- **Facts learned** about the project, codebase, or user's environment
- **Instructions given** by the user ("always do X", "never do Y", "I prefer Z")
- **Goals and commitments** discussed or agreed upon
- **Errors and lessons** from debugging or failed approaches

> **CRITICAL**: You MUST explicitly pass the memory content, `--type`, `--confidence`, `--provenance <type>`, and `--source <your_agent_name>` (e.g., `--source claude_code`) with every `memanto remember` command. Do NOT let it default.

Do NOT wait until asked. If the user says "I prefer tabs over spaces", immediately run:
`memanto remember "User prefers tabs over spaces for indentation" --type preference --source <your_agent_name> --provenance explicit_statement`

### Commands

```bash
memanto remember "content" --type <type> --confidence <0.0-1.0> --provenance <provenance> --source <agent_name>  # Store a memory
memanto recall "query"                       # Search memories
memanto answer "question"                    # RAG-powered answer from memory
memanto memory sync --project-dir .          # Re-sync MEMORY.md
```

Memory types: fact, preference, instruction, decision, event, goal, commitment,
observation, learning, relationship, context, artifact, error.
{note_line}
{MEMANTO_SENTINEL_END}"""


def get_instruction_content(agent_name: str) -> str:
    """Get MEMANTO instruction section content for a specific agent."""
    templates = {
        "claude-code": _base_instruction_content(
            tool_phrase="the Bash tool",
            note_suffix="The `memanto-memory` skill contains reference guidelines only (best practices, confidence levels, tagging). It is NOT executable — always use Bash for memanto commands.",
        ),
        "codex": _base_instruction_content(
            tool_phrase="the terminal",
            note_suffix="The `memanto-memory` skill in `.agents/skills/memanto/` contains detailed reference guidelines (best practices, confidence levels, tagging).",
        ),
        "cursor": _get_mdc_content(),
        "windsurf": _base_instruction_content(
            tool_phrase="the terminal",
            note_suffix="The `memanto-memory` skill in `.windsurf/skills/memanto/` contains detailed reference guidelines.",
        ),
        "gemini-cli": _base_instruction_content(
            tool_phrase="the terminal",
            note_suffix="The `memanto-memory` skill in `.gemini/skills/memanto/` contains detailed reference guidelines.",
        ),
        "cline": _base_instruction_content(
            tool_phrase="the terminal",
            note_suffix="Run `memanto memory sync --project-dir .` at the start of each session to populate MEMORY.md.",
        ),
        "continue": _base_instruction_content(
            tool_phrase="the terminal",
            note_suffix="Run `memanto memory sync --project-dir .` at the start of each session to populate MEMORY.md.",
        ),
        "opencode": _base_instruction_content(
            tool_phrase="the terminal",
            note_suffix="The `memanto-memory` skill in `.agents/skills/memanto/` contains detailed reference guidelines.",
        ),
        "roo": _base_instruction_content(
            tool_phrase="the terminal",
            note_suffix="Run `memanto memory sync --project-dir .` at the start of each session to populate MEMORY.md.",
        ),
        "github-copilot": _base_instruction_content(
            tool_phrase="the terminal",
            note_suffix="Run `memanto memory sync --project-dir .` at the start of each session to populate MEMORY.md.",
        ),
        "augment": _base_instruction_content(
            tool_phrase="the terminal",
            note_suffix="The `memanto-memory` skill in `.augment/skills/memanto/` contains detailed reference guidelines.",
        ),
    }
    return templates.get(agent_name, _base_instruction_content())


def _get_mdc_content() -> str:
    """Get MDC-formatted rules content for Cursor."""
    return f"""---
description: MEMANTO persistent memory integration - manages memory sync, storage, and retrieval
alwaysApply: true
---

{MEMANTO_SENTINEL}

# MEMANTO Memory Integration

This project is connected to **MEMANTO** — a persistent memory system.

## MANDATORY: Sync and Read MEMORY.md First

At session start, run in the terminal:
```bash
memanto memory sync --project-dir .
```

Then read `MEMORY.md` in the project root. It contains the user's preferences,
facts, goals, instructions, decisions, and commitments from all previous sessions.
You MUST follow any instructions and preferences found there.

## MANDATORY: Search Memory Before Giving Up

When unsure about past context, decisions, or preferences, search memory first:
```bash
memanto recall "query"
memanto answer "question"
```

## MANDATORY: Store Memories Proactively

Store important information discovered during this session:
```bash
memanto remember "content" --type <type> --tags "tag1,tag2" --confidence <0.0-1.0> --provenance <provenance> --source <agent_name>
```

Types: fact, preference, instruction, decision, event, goal, commitment,
observation, learning, relationship, context, artifact, error.

Store: user preferences, decisions made, facts learned, instructions given,
goals discussed, errors encountered. Do NOT wait until asked.

> **CRITICAL**: You MUST explicitly pass the memory content, `--type`, `--confidence`, `--provenance <type>`, and `--source <your_agent_name>` with every `memanto remember` command. Do NOT let it default.

{MEMANTO_SENTINEL_END}"""


def get_skill_content() -> str:
    """Get the SKILL.md content (shared across all agents)."""
    return SKILL_MD_CONTENT.strip() + "\n"
