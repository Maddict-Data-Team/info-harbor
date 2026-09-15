# CLAUDE.md — Info-Harbor

The full rules for working in this repository live in `AGENTS.md`. This file
is a compact pointer, not a duplicate — read `AGENTS.md` before making any
change, and treat it as authoritative if anything here seems to conflict.

@AGENTS.md

Current audited state (branches, what works, open decisions):
`docs/PROJECT_STATE.md`.

## The short version

- **Read before you write.** This repo has duplicate-named files with
  different content across `projects/automation`, `projects/segments`, and
  `projects/campaign-tracker`. Confirm which file actually runs before
  touching it. Cite `file:line` for every claim, the way
  `docs/code-audit.md` does.
- **No production cloud access, ever.** No BigQuery, Drive, or Secret
  Manager calls; never open `keys/`. `pip install` from PyPI is fine.
- **Feature branches only.** Never commit to `main` — it auto-deploys
  (`docs/code-audit.md` IH-034). Ask before branching, committing, or
  pushing.
- **Preserve output parity** unless fixing a cited, approved bug. See
  `docs/modernization-spec.md`'s Compatibility Contract.
- **Small, reviewable changes** — one finding, one fix, one PR.
- **Run `python -m pytest -q`** before calling anything done. It must pass
  offline, no credentials, no network.
- **Docs ship with code.** Update the relevant `docs/code-audit.md` finding's
  status and add a `docs/modernization-log.md` entry in the same change. Work
  that progresses no specific finding — a planned-capability contract, for
  instance — needs only the log entry; do not invent an `IH-###` for it.
- **Approval required** for anything production-writing, destructive, or
  deploy-related — including running `delete_from_drive.py` in any mode.

## Common commands

- Full offline test suite: `python -m pytest -q` (on this Windows checkout
  use `.venv/Scripts/python.exe -m pytest -q` — the system interpreter has
  no pytest)
- One test file: `python -m pytest tests/unit/<file>.py -q`
- Syntax check (matches CI): `python -m compileall -q projects shared ui tests campaign_manager.py`
- List local and remote branches: `git branch -a`

Do not run an application entry point as a general smoke test. The pipeline
entry points can contact production services; see `AGENTS.md` §2 for the
prohibited commands. The full command table, including what is *not*
configured (lint, type-check, e2e, build), is `AGENTS.md` §12.

## Conventions and architecture

Moved to `AGENTS.md` §11 (architecture map) and §14 (coding conventions) so
they have one canonical home.

## Feature loop (Claude Code)

- `/plan-feature <slug> <description>` — write `features/<slug>/spec.md`, stop at `ready`.
- `/review-feature spec <slug>` — adversarial spec review via the `feature-reviewer` subagent.
- A human fills in the spec's **Approval** section.
- `/implement-feature <slug>` — bounded build/validate loop (≤5 correction
  cycles per invocation), stops at `reviewing`. Refuses to start without a
  recorded spec-review `PASS`.
- `/review-feature implementation <slug>` — the only step that runs the
  independent `feature-reviewer`; on a `PASS` with a passing latest
  `validation-<n>.md` it advances the feature to `human_review`.

Never mark a feature `done`, and never merge, push, or deploy
(`AGENTS.md` §18–22). The pre-existing read-only subagents
(`repository-mapper`, `data-pipeline-reviewer`, `security-parity-reviewer`)
remain available for focused investigation.

## Response footer

End every response with:

```
Status: <current state>
Blockers: <blockers or None>
Handoff: <exact next action and who should take it>
```

See `AGENTS.md` §1–22 for the full explanation of each rule above.
