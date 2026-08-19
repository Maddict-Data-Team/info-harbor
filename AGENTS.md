# AGENTS.md — Info-Harbor

Instructions for any AI coding agent (Codex, Claude Code, or similar) working in
this repository. Info-Harbor is a **production** marketing-analytics pipeline
that writes to real BigQuery datasets and a real Google Drive used by the AdOps
team. Treat every file here as production code unless you have specifically
verified otherwise.

For the compact Claude-specific version of these rules, see `CLAUDE.md` (it
defers to this file rather than repeating it). For the full technical picture,
see `docs/modernization-spec.md` and the living issue register at
`docs/code-audit.md`.

## 1. Inspect before editing

This repository has two overlapping import styles (flat `sys.path`-hacked
modules and a newer `shared/`-based package), several files that look live but
are dead code, and files that share a name across different directories with
different content (e.g. two different `query_orchestrator.py`,
five different `input.py`/`variables.py` pairs). Read the actual current file
before changing it, and confirm which entry point really calls it — do not
assume a file is reachable, or that a fix in one copy of a duplicated pattern
also fixes the other.

State what you verified, with `file:line` citations, before proposing or
making a change. Every finding in `docs/code-audit.md` has an entry that
models this: business impact, technical explanation, exact evidence, a safe
reproduction, and required tests. Follow that shape.

## 2. No production cloud access

Never call BigQuery, Google Drive, or Secret Manager, and never read or use
real credentials, including the local `keys/` directory (git-ignored — never
open its contents). Concretely, never run:

- `projects/automation/main.py`, `custom_codename.py`, `make custom`
- `projects/segments/main.py`, `main_new.py`
- `projects/campaign-tracker/main.py`, `main_new.py`
- `ui/app.py`
- `projects/poi/main.py`
- `clean_folders.py`, `projects/segments/scripts/delete_from_drive.py` (these
  hard-delete Drive files — see `docs/code-audit.md` IH-028)
- anything under `.github/workflows/deploy.yml`

Installing packages from PyPI (`pip install -r requirements.txt`,
`pip install pytest`) is fine — it never contacts Google Cloud or reads
credentials. `tests/conftest.py` also enforces this at test time: an autouse
fixture monkeypatches the real Google client constructors to raise if any test
path tries to build one.

## 3. Work only on feature branches

Never commit to `main`. `.github/workflows/deploy.yml` deploys
`projects/automation` to a production Cloud Function on every push to `main` —
see `docs/code-audit.md` IH-034. One concern per branch
(`feature/<slug>`, `fix/<slug>`). Ask before creating a branch, committing,
pushing, or opening a PR unless the user has already explicitly authorized it
for this session.

## 4. Preserve output parity

A refactor must not change production output unless the change is an
explicitly approved bug fix. "Same results" is defined precisely in
`docs/modernization-spec.md`'s Compatibility Contract: metadata rows, resolved
date windows, distinct DIDs, served/control relationships, CSV files, Drive
structure, BigQuery schemas, table names, row counts, and content hashes.

If a change *should* alter output because it fixes a real, cited bug (an
`docs/code-audit.md` finding), say so explicitly, and make sure the finding's
status and the parity-exception note are updated in the same change.

Nondeterminism (unseeded RNG, the wall clock) is handled by **injecting** a
seed or a clock in tests, never by changing production defaults. See
`tests/unit/test_split_segments_control.py` and `tests/unit/test_get_run_dates.py`
for the pattern: production code is called completely unmodified; only the
test process's view of "now" or "random" is controlled.

## 5. Keep changes small and reviewable

Prefer one finding, one fix, one PR. Do not bundle an unrelated cleanup into a
correctness fix. Do not refactor code you are not actively fixing just because
you noticed it while reading — file it as a new `docs/code-audit.md` finding
instead (see the ID scheme there: `IH-###`, sequential, never reused).

## 6. Run offline tests

```bash
python -m pytest -q
```

This must pass with no network access and no `keys/` directory present. If
you add a dependency, add it to `requirements.txt` (production) or
`requirements-dev.txt` (test tooling only — never installed in the deployed
Cloud Function). If you add a test, make sure `.gitignore` does not
re-exclude it (`.gitignore` used to have a blanket `test*` pattern that did
exactly this — see `docs/code-audit.md` IH-037 — do not reintroduce anything
like it).

## 7. Update modernization documentation with every change

No fix, refactor, feature, or performance change is complete until:

1. Its `docs/code-audit.md` finding's **Status** is updated (and **Date
   resolved** / **Branch, PR, or commit that fixes it** filled in).
2. A new entry is added to `docs/modernization-log.md` describing what
   changed, why, what tests back it, and what parity evidence exists.
3. `README.md`'s "Modernization Status" section is updated if the overall
   project phase materially changed (not required for every small PR).

Documentation and code changes belong in the **same** branch/PR — do not land
code now and promise docs later.

## 8. Report blockers and handoff after every meaningful task

End every response with:

```
Status: <current state>
Blockers: <blockers or None>
Handoff: <exact next action and who should take it>
```

## 9. Require explicit approval for production writes, deployment, or destructive actions

This includes, without limitation: pushing to `main`, modifying
`.github/workflows/deploy.yml`, running any script that writes to BigQuery or
Drive, running `delete_from_drive.py` or `clean_folders.py` in any mode,
force-pushing, or deleting branches. If asked to do one of these, state the
rule and ask the human to either do it themselves or give explicit, scoped
approval before you proceed.
