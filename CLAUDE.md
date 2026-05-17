# DeerFlow — Claude Code Context

This is the root-level CLAUDE.md. Sub-project CLAUDE.md files exist at:
- `backend/CLAUDE.md` — full backend architecture, commands, and conventions
- `frontend/CLAUDE.md` — frontend architecture and conventions

---

## Active Study Branch

The current branch `study` is a **technical case study branch**.
It contains inline annotations (`[DL-*]` tags) and the `notes/` directory.
Never merge study annotations into `main`.

---

## Study Notes Directory

All study notes live in `notes/`. This directory is read and written by both
the developer and Claude Code during study sessions.

```
notes/
├── study_plan.md              # Master list of study sections (source of truth)
├── note_taking_approach.md    # Annotation conventions and git workflow
├── architecture/              # System-level design notes
├── modules/                   # Per-module deep-dives
├── execution-flow/            # Request lifecycle traces
├── patterns/                  # Design patterns found in the codebase
├── questions/                 # Open questions and hypotheses
├── glossary/                  # DeerFlow-specific terms
└── weekly-findings/           # Periodic study summaries
```

### study_plan.md

`notes/study_plan.md` is the authoritative list of 29 study sections in top-down order.
Each section has:
- A **goal** — what to understand by the end
- **Key files** — the primary files to read
- A **status** (`[ ]` not started · `[~]` in progress · `[x]` complete)

The plan is updated regularly as the study evolves. Always read it before starting a session.

---

## Inline Annotation Convention

Study annotations inside source files use these tags:

| Tag | Meaning |
|-----|---------|
| `# [DL-NOTE]` | General observation |
| `# [DL-INSIGHT]` | Architectural or design insight |
| `# [DL-QUESTION]` | Unclear — needs further investigation |
| `# [DL-TODO]` | Follow-up needed |
| `# [DL-WARN]` | Potential gotcha or subtle risk |

Use `// [DL-*]` for TypeScript/JavaScript files.

Keep inline comments to **1–2 lines maximum**. Long explanations go in `notes/`.

Search all annotations:
```bash
grep -R "DL-" backend/ frontend/src/ --include="*.py" --include="*.ts" --include="*.tsx"
```

---

## Custom Study Commands

Four project-level commands live in `.claude/commands/`. All use `|` as the delimiter
between the primary argument and extra instructions.

### `/study-plan [action or question] | [extra instructions]`

Discuss, review, or update `notes/study_plan.md`.

Actions: view progress · split a section · create a section · delete a section · reorder · mark status.

Structural changes (split, create, delete) are proposed before editing unless unambiguous.

### `/study-code [section-number or file-path] | [extra instructions]`

Explain code and add `[DL-*]` annotations to source files.

- Section number → reads that section's key files from `notes/study_plan.md`
- File or folder path → uses it directly

Produces: inline annotations in source files + a structured explanation.
Does **not** create notes/ files.

### `/study-doc [section-number] | [extra instructions]`

Document a full section **with checkpoint pauses**.

Phases: Setup → per-file reading (pause after each) → notes file creation → finalise.

Produces: `[DL-*]` annotations in all key source files + primary notes file in `notes/` +
optional secondary files (execution-flow/, patterns/) + updated study_plan.md.

### `/study-doc-fast [section-number] | [extra instructions]`

Document a full section **without checkpoint pauses** — reads all key files in one pass,
then creates notes files. Best for smaller or lower-priority sections.

Same output contract as `/study-doc`.

---

### Study depth expectation (all doc commands)

- Read every line of every key file — no skimming
- Follow imports, callsites, and test files to build complete context
- Explain *why* the code is designed this way, not just *what* it does
- Include Mermaid diagrams in notes files (sequence diagram for 3+ actor flows,
  flowchart for state machines, graph for dependency maps)
- Surface open questions in `notes/questions/open-questions.md`

---

## Purpose of This Study

The study produces:
1. A deep technical understanding of DeerFlow for the developer
2. A set of annotated notes (`notes/`) as a durable knowledge base
3. Technical writing for Medium articles (soap-opera structured, section by section)

Every insight captured here is input to the Medium article series.
Write notes as if explaining to a skilled engineer encountering DeerFlow for the first time.
