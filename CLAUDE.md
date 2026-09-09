# CLAUDE.md — Info-Harbor

The full rules for working in this repository live in `AGENTS.md`. This file
is a compact pointer, not a duplicate — read `AGENTS.md` before making any
change, and treat it as authoritative if anything here seems to conflict.

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

- Full offline test suite: `python -m pytest -q`
- One test file: `python -m pytest tests/unit/<file>.py -q`
- Syntax check: `python -m compileall -q shared projects ui`
- List local and remote branches: `git branch -a`

Do not run an application entry point as a general smoke test. The pipeline
entry points can contact production services; see `AGENTS.md` §2 for the
prohibited commands.

## Conventions

- Confirm the live entry point before editing: duplicate module names do not
  imply duplicate behavior.
- Keep new configuration additive and typed. Do not silently merge legacy
  values that differ by application.
- Preserve output parity by default. Any approved behavior change must cite
  its audit finding and document the deliberate parity exception.
- Do not add new `sys.path` mutation or generic same-name imports. Use an
  explicit package or explicit file path when legacy module names collide.
- Keep cross-domain business code out of catch-all `utils` or `common`
  directories. Generic helpers must be pure and genuinely shared.
- New cloud-facing code must be testable with the offline fakes. Never log
  credentials, tokens, raw device identifiers, or sensitive query values.

## Architecture quick map

- `projects/automation/`: current Cloud Function source. CI currently uploads
  this directory alone; do not assume root-level modules are included in its
  deployment artifact.
- `projects/segments/`, `projects/poi/`, and `projects/campaign-tracker/`:
  legacy workflows being migrated incrementally.
- `ui/`: the current Flask operations application.
- `shared/config/settings.py`: additive shared-settings foundation. Legacy
  `variables.py` and `input.py` files remain authoritative for a component
  until its field-level parity is proven.
- `shared/config/environment.py`, `shared/config/source_allowlist.py`,
  `shared/config/output_policy.py`: Phase A safety contracts. Additive,
  imported by no live entry point, and **not enforced at runtime** — they
  state the test/production boundary, they do not police it, and their
  presence authorizes no cloud testing. Wiring them into an entry point is
  Phase B and needs explicit approval.
- `tests/`: offline unit tests, fakes, fixtures, and parity helpers.
- `docs/architecture-and-test-environment-plan.md`: accepted target
  architecture and production-read/test-write boundary.
- `docs/code-audit.md`: living issue register. `docs/modernization-log.md`:
  chronological change record.

## Response footer

End every response with:

```
Status: <current state>
Blockers: <blockers or None>
Handoff: <exact next action and who should take it>
```

See `AGENTS.md` §1–9 for the full explanation of each rule above.
