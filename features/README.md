# Feature Loop — Info-Harbor

This directory is where every new feature or fix moves through the project's
loop-engineering workflow:

```text
planning → specification review → human approval → implementation
        → automated validation → independent review → human review → done
```

It is built on top of, and does not replace, the existing modernization
records:

| Record | Role | Still authoritative for |
|---|---|---|
| `AGENTS.md` | Canonical rules for every agent | Safety, Git, parity, definition of done |
| `docs/PROJECT_STATE.md` | Evidence-based current-state snapshot | What exists, what is broken, what is open |
| `docs/code-audit.md` | Per-defect register (`IH-###`) | Defect evidence and status |
| `docs/modernization-log.md` | Chronological change log | What changed, when, with what tests |
| `features/QUEUE.md` | Loop state for every feature | Which state each item is in |
| `features/<slug>/spec.md` | One feature's approved contract | Scope, acceptance criteria, verification |
| `features/<slug>/verification/` | Evidence for that feature | Commands run, results, review verdicts |

A feature that fixes an audit finding **links** to its `IH-###` entry; it does
not duplicate the finding's evidence. When the feature lands, the finding's
status and the modernization log are still updated as `AGENTS.md` §7 requires.

## Directory layout

```text
features/
├── README.md              this file
├── QUEUE.md               single source of truth for loop state
├── _template/
│   ├── spec.md            copy to features/<slug>/spec.md
│   └── verification/
│       └── README.md      evidence conventions
└── <slug>/                one directory per feature (kebab-case slug)
    ├── spec.md
    ├── mock.html          optional — only when UI behavior benefits
    └── verification/
        ├── spec-review-<n>.md
        ├── pre-existing-state-<n>.md
        ├── validation-<n>.md
        └── implementation-review-<n>.md
```

Slugs are short and kebab-case. A slug for an audit fix should start with the
finding ID, e.g. `ih-028-delete-from-drive-confirm`.

## States

| State | Meaning | Who may set it |
|---|---|---|
| `idea` | Recorded, not yet planned | Anyone |
| `planning` | `/plan-feature` is drafting the spec, or the spec failed review | Planner |
| `ready` | Spec complete, no blocking questions; **awaiting human approval** | Planner |
| `building` | Human approved the spec; `/implement-feature` is running or fixing reviewer findings | Builder |
| `reviewing` | Automated validation passed; independent review in progress | Builder / `/review-feature` |
| `human_review` | The latest `validation-<n>.md` passed **and** `/review-feature implementation` recorded a `feature-reviewer` `PASS` in `implementation-review-<n>.md` | `/review-feature` only |
| `done` | A human accepted the work (and merged it through the normal PR process) | **Human only** |
| `blocked` | Cannot progress without a decision, access, or approval; the note says which | Anyone |

Rules:

- A builder may never mark its own work `done`. No agent may set `done`.
- `ready` does **not** mean approved. Implementation requires the spec's
  **Approval** section to be filled in by a human.
- `/implement-feature` also refuses to start without a recorded
  `verification/spec-review-<n>.md` whose latest verdict is `PASS`.
- A reviewer `FAIL` moves a feature back to `building` (implementation) or
  `planning` (specification).
- The independent implementation review is performed and recorded **only** by
  `/review-feature implementation <slug>`. `/implement-feature` never invokes
  `feature-reviewer` itself, never writes `implementation-review-<n>.md`, and
  never sets `human_review`; it stops at `reviewing` and hands off.
- Uncertain historical work is never marked `done`; it is `blocked`,
  `reviewing`, or `human_review` with an explanatory note.

## Skills and agents

| Name | Kind | Location | Purpose |
|---|---|---|---|
| `/plan-feature` | Skill | `.claude/skills/plan-feature/SKILL.md` | Draft or update a spec; stop at `ready` |
| `/implement-feature` | Skill | `.claude/skills/implement-feature/SKILL.md` | Bounded Level-1 build → validate loop; stop at `reviewing` and hand off to `/review-feature implementation` |
| `/review-feature` | Skill | `.claude/skills/review-feature/SKILL.md` | Adversarial spec or implementation review; record verdict |
| `feature-reviewer` | Subagent | `.claude/agents/feature-reviewer.md` | Fresh-context, adversarial `PASS`/`FAIL` reviewer |
| `repository-mapper`, `data-pipeline-reviewer`, `security-parity-reviewer` | Subagents | `.claude/agents/` | Pre-existing read-only specialists; `feature-reviewer` may be supplemented by them, never replaced |

Codex mirrors of the three pre-existing specialists exist, untracked, under
`.codex/agents/*.toml`. No Codex mirror of the loop skills has been created;
see `docs/PROJECT_STATE.md` for that open decision.
