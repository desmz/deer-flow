# Note-Taking Approach

This document defines the methodology for the DeerFlow technical case study.
Both human and Claude Code follow these conventions consistently.

---

## 1. Comment Delimiter Strategy

Use structured prefixes inside source files to tag study annotations.
Keep inline comments **short** — one or two lines maximum.
Long explanations belong in markdown notes (see Section 2).

| Tag | Purpose |
|-----|---------|
| `# [DL-NOTE]` | General observation about the code |
| `# [DL-INSIGHT]` | Architectural or design insight worth highlighting |
| `# [DL-QUESTION]` | Something unclear or worth investigating further |
| `# [DL-TODO]` | Follow-up investigation needed |
| `# [DL-WARN]` | Potential gotcha, edge case, or subtle bug risk |

**TypeScript/JavaScript equivalent:** Use `// [DL-*]` with the same tags.

### Example (Python)

```python
# [DL-INSIGHT] This is not a simple dispatcher — it's a state machine transition.
# The retry logic is embedded inside the callback chain, not in the caller.
async def run_agent(thread_id: str, ...) -> AsyncIterator[RunEvent]:
    ...
```

### Example (TypeScript)

```typescript
// [DL-QUESTION] Why SSE here instead of WebSockets? Check stream_bridge_config.
const response = await fetch('/api/runs/stream', ...)
```

### Searching annotations

```bash
# All annotations
grep -R "DL-" backend/ frontend/src/ --include="*.py" --include="*.ts" --include="*.tsx"

# Specific type
grep -R "DL-INSIGHT" .

# Per file
grep "DL-" backend/packages/harness/deerflow/runtime/runs/*.py
```

---

## 2. Notes Directory Structure

```
notes/
├── study_plan.md              # Master study plan (source of truth for sections)
├── note_taking_approach.md    # This file
├── architecture/              # System-level design notes
├── modules/                   # Per-module deep-dives
├── execution-flow/            # Request lifecycle and data flow traces
├── patterns/                  # Design patterns identified in the codebase
├── questions/                 # Open questions and hypotheses
├── glossary/                  # DeerFlow-specific terms and concepts
└── weekly-findings/           # Periodic summary of study progress
```

### Note file template

Each module note should follow this structure:

```markdown
# <Module Name>

## Purpose
One paragraph describing what this module does and why it exists.

## Key Files
- `path/to/file.py` — what it contains
- `path/to/other.py` — what it contains

## Important Concepts
- concept one
- concept two

## Execution Flow
Step-by-step trace of how data moves through this module.

## My Insights
Architectural observations, design decisions, and comparisons to other patterns.

## Questions
- Unresolved questions to investigate
- Hypotheses to verify

## Links to Related Modules
- [[module-name]] — relationship description
```

---

## 3. Git Workflow

### Branch model

```
main    → clean sync with upstream (never study here)
study   → active annotated branch (current)
```

### Commit convention

```
study(runtime): analyze task scheduling
study(memory): add notes on persistence layer
study(agent): annotate retry pipeline
```

### Weekly update workflow

```bash
# Step 1: Save study work
git checkout study
git add .
git commit -m "study(section-XX): notes and annotations"

# Step 2: Update clean main from upstream
git checkout main
git fetch upstream
git merge upstream/main

# Step 3: Rebase study on top of latest main
git checkout study
git rebase main
```

Rebase (not merge) keeps the mental model: *annotations sit on top of the latest source*.

---

## 4. Conflict Resolution Strategy

Conflicts happen when upstream edits lines near your comments.

### Decision framework

| Scenario | Action |
|----------|--------|
| Upstream changed logic heavily | Keep upstream version; rewrite your note after |
| Only formatting/refactor changed | Manually reinsert your comment |
| Function deleted upstream | Move notes to `notes/deprecated/` |

### Minimizing conflicts

- Keep inline comments to **one or two lines** — never multi-line essays
- Put all long explanations in `notes/modules/` markdown files
- Use `[DL-*]` tags to make comments trivially identifiable and re-insertable

---

## 5. Balance: Inline vs Markdown

### Use inline comments for
- Tiny insights that are inseparable from the specific line
- Navigation markers pointing to deeper notes
- Flagging gotchas at the point of the code

### Use markdown notes for
- Architecture understanding
- Execution flow traces
- Long explanations and diagrams
- Comparisons to other frameworks
- Open hypotheses

**Target ratio:** 1–2 inline comment lines per insight; full depth in markdown.

---

## 6. Naming Conventions

### Note files

```
notes/modules/agent-runtime.md
notes/modules/task-orchestrator.md
notes/execution-flow/request-lifecycle.md
notes/architecture/component-map.md
notes/patterns/middleware-composition.md
```

### Deprecated notes

When upstream removes or restructures something your notes cover:

```
notes/deprecated/v2-agent-factory-pre-refactor.md
```

---

## 7. Core Principle

> Inline comments are temporary anchors.
> Markdown notes are the durable asset.

The `notes/` directory is what survives upstream evolution.
The `[DL-*]` tags are what survives rebases cleanly.
Together they produce the technical writing that goes to Medium.
