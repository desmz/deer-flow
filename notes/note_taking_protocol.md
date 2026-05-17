# Note-Taking Protocol

How to organize case study files across the `notes/` folder structure.
Each study section produces multiple outputs that go into different folders based on content type.

---

## How Sections Map to Folders

A single study section typically produces **one primary file + optional secondary files**:

```
notes/
├── architecture/     ← Sections 01–04, 28 (system-level thinking)
├── modules/          ← Sections 05–27 (per-module deep-dives, primary output)
├── execution-flow/   ← Any section that traces a request/data path end-to-end
├── patterns/         ← Section 29 + any pattern discovered mid-study
├── questions/        ← Open questions surfaced during any section
├── glossary/         ← Terms and concepts defined during any section
└── weekly-findings/  ← Periodic roll-ups across sections
```

---

## Naming Convention

Use `{section-number}-{slug}.md` so files sort and are traceable to the plan:

```
notes/
├── architecture/
│   ├── 01-product-overview.md
│   ├── 02-system-architecture.md
│   ├── 03-project-setup.md
│   ├── 04-infrastructure-devops.md
│   └── 28-extension-points.md
│
├── modules/
│   ├── 05-gateway-api.md
│   ├── 06-auth-authorization.md
│   ├── 07-langgraph-runtime.md
│   │   07a-stream-bridge.md        ← split if module is huge
│   │   07b-checkpointer.md
│   ├── 08-lead-agent.md
│   ├── 09-middleware-pipeline.md
│   ├── 10-memory-system.md
│   ├── ...
│   ├── 22-frontend-architecture.md
│   ├── 23-frontend-core-modules.md
│   ├── 24-frontend-workspace-ui.md
│   ├── 25-frontend-streaming.md
│   ├── 26-testing-strategy.md
│   └── 27-security-design.md
│
├── execution-flow/
│   ├── request-lifecycle.md        ← produced during Section 02 or 07
│   ├── memory-update-flow.md       ← produced during Section 10
│   └── skill-execution-flow.md     ← produced during Section 13
│
├── patterns/
│   ├── 29-patterns-insights.md     ← Section 29's primary file
│   ├── middleware-composition.md   ← discovered mid-study (e.g. Section 09)
│   └── debounce-batch-pattern.md   ← discovered mid-study (e.g. Section 10)
│
├── questions/
│   └── open-questions.md           ← running log across all sections
│
├── glossary/
│   └── deerflow-terms.md           ← running glossary
│
└── weekly-findings/
    └── 2026-W20.md                 ← weekly roll-up
```

---

## The Rule for Splitting

| Situation | What to do |
|-----------|-----------|
| Module fits in one read | One file: `modules/07-langgraph-runtime.md` |
| Module is very large (e.g. runtime has 6+ sub-systems) | Split: `07-langgraph-runtime.md` as index + `07a-stream-bridge.md`, `07b-checkpointer.md` as sub-files |
| Cross-cutting flow discovered during any section | Extra file in `execution-flow/` |
| New pattern identified | Extra file in `patterns/` |
| Open question surfaced | Append to `questions/open-questions.md` |

---

## study_plan.md Progress Tracker

The **Notes File** column in `study_plan.md` should link to the **primary file** for that section:

```markdown
| 07 | Backend: LangGraph Runtime | [x] | `modules/07-langgraph-runtime.md` |
```

This makes the plan the single navigation entry point — click the link, reach the notes.

---

## Summary

- Folders = content type
- Filenames = section number + slug
- One primary file per section goes in the most relevant folder
- Secondary outputs (flows, patterns, questions) scatter into their semantic homes and get linked from the primary file
