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
  status and add a `docs/modernization-log.md` entry in the same change.
- **Approval required** for anything production-writing, destructive, or
  deploy-related — including running `delete_from_drive.py` in any mode.

## Response footer

End every response with:

```
Status: <current state>
Blockers: <blockers or None>
Handoff: <exact next action and who should take it>
```

See `AGENTS.md` §1–9 for the full explanation of each rule above.
