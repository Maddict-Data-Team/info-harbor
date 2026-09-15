# Feature: <Feature name>

| Field | Value |
|---|---|
| Slug | `<kebab-case-slug>` |
| Queue status | `planning` |
| Related audit findings | `IH-###` (or "none — capability work") |
| Proposed branch | `feature/<slug>` or `fix/<slug>` |
| Base branch | `<branch @ short sha>` — see `docs/PROJECT_STATE.md` for the open base-branch decision |
| Spec author | `<planner>` |
| Last updated | `YYYY-MM-DD` |

## Approval

> Filled in **only by a human**. `/implement-feature` refuses to start while
> any field here is blank or `Approved` is not `yes`.

- Approved: `<yes | no>`
- Approved by: `<name>`
- Date: `YYYY-MM-DD`
- Approval scope / conditions: `<e.g. "parity exception for IH-### approved">`

## Background

What exists today, with `file:line` evidence. Link the relevant
`docs/code-audit.md` entry instead of copying it.

## Problem

The concrete failure, risk, or missing capability — who is affected and how.

## Goal

One or two sentences describing the outcome.

## User stories

- As a `<role>`, I want `<capability>` so that `<benefit>`.

## In scope

-

## Out of scope

- Anything not listed under "In scope".
- Production cloud access, deployment changes, and `main` (see `AGENTS.md` §2, §3, §9).

## Functional requirements

| ID | Requirement |
|---|---|
| FR-1 | |

## UI and interaction requirements

`Not applicable — no UI change` **or** the pages, routes, templates
(`ui/templates/*.html`, Bootstrap 5.3 per `ui/templates/base.html`), and
interactions affected. Link `mock.html` if one exists.

## Loading, empty, validation, error, and success states

| State | Trigger | Observable behavior (message, HTTP status, exit code, log line) |
|---|---|---|
| Loading | | |
| Empty | | |
| Validation error | | |
| Runtime error | | |
| Success | | |

For CLI and pipeline work, "state" means the exit code, stdout/stderr text,
and HTTP status a caller observes.

## Accessibility requirements

`Not applicable — no UI change` **or** keyboard operability, labels, focus,
contrast, and non-color status indicators for every changed UI element.

## Security and privacy considerations

- Credentials / `keys/` / Secret Manager touched? `<no | how>`
- New write path to BigQuery or Drive? `<no | which, and its safety gate>`
- New input reaching SQL or a Drive query string (`IH-030`)? `<no | how it is escaped/parameterized>`
- Authentication impact on `ui/app.py` routes (`IH-025`)? `<no | which>`
- Logs must not contain secrets, tokens, raw DIDs, or sensitive query values.

## Data and migration impact

- BigQuery schema change: `<none | detail>`
- Output parity impact (`docs/modernization-spec.md` §6): `<none | deliberate exception — cite IH-### and before/after>`
- Drive structure change: `<none | detail>`
- Migration / backfill needed: `<none | detail — never run automatically>`

## Files likely to change

| File | Why | Live entry point that reaches it (verified) |
|---|---|---|
| | | |

## Dependencies

Other features, findings, decisions, packages, or branches this relies on.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| | | | |

## Observable acceptance criteria

Each criterion must be checkable by a command, a test, or a described
observation. Never "works correctly".

| ID | Given / When / Then |
|---|---|
| AC-1 | Given …, when …, then … |

## Verification map

Every acceptance criterion maps to at least one verification method.

| AC | Method (automated test / command / manual step) | Evidence file |
|---|---|---|
| AC-1 | `python -m pytest tests/unit/test_<name>.py -q` → test `<test_id>` passes | `verification/validation-<n>.md` |

## Automated verification

Commands that must pass (see `AGENTS.md` "Validation commands"):

```bash
python -m pytest -q
```

```bash
python -m compileall -q projects shared ui tests campaign_manager.py
```

Plus any feature-specific test files.

## Manual verification

`None required` **or** numbered steps a human or builder performs, which must
never include running a prohibited entry point (`AGENTS.md` §2).

## Evidence requirements

- Validation record for the final passing cycle.
- Implementation review with verdict `PASS`.
- `<screenshots / extra records required by this feature>`

## Open questions

| # | Question | Blocking? | Owner | Answer |
|---|---|---|---|---|
| 1 | | yes/no | | |

`/implement-feature` refuses to start while any **blocking** question is
unanswered.

## Retry limit

- Unsuccessful validation-correction cycles before stopping as `blocked`: **5** (may be lowered, never raised above 5)
- Reviewer `FAIL` → fix rounds before stopping as `blocked`: **3**

## Rollback considerations

How to undo this change (normally `git revert <sha>` of one focused commit),
what else must be reverted together, and any data or configuration that a
revert would not restore.

## Definition of done

- [ ] Every acceptance criterion satisfied, with evidence
- [ ] `python -m pytest -q` and every command under "Automated verification" pass
- [ ] Manual verification completed (or recorded as not required)
- [ ] Verification evidence recorded under `verification/`
- [ ] `feature-reviewer` returned `PASS`
- [ ] No unexplained unrelated changes in `git diff`
- [ ] `docs/code-audit.md` finding status and `docs/modernization-log.md` entry updated in the same change (`AGENTS.md` §7)
- [ ] Queue moved to `human_review` by `/review-feature implementation` on a recorded reviewer `PASS`
- [ ] A **human** moves the queue to `done` after accepting and merging through the normal PR process
