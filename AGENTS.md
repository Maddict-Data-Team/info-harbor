# AGENTS.md — Info-Harbor

Instructions for any AI coding agent (Codex, Claude Code, or similar) working in
this repository. Info-Harbor is a **production** marketing-analytics pipeline
that writes to real BigQuery datasets and a real Google Drive used by the AdOps
team. Treat every file here as production code unless you have specifically
verified otherwise.

For the compact Claude-specific version of these rules, see `CLAUDE.md` (it
defers to this file rather than repeating it). For the full technical picture,
see `docs/modernization-spec.md` and the living issue register at
`docs/code-audit.md`. For the evidence-based current state of the repository —
branches, what works, what is broken, what is undecided — read
`docs/PROJECT_STATE.md` first. New features and fixes follow the loop in §18.

This file is the canonical instruction set. There are no nested `AGENTS.md`
files; if one is ever added, it applies only to its own directory tree and may
narrow, never loosen, these rules.

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

## 10. Product and repository status

Info-Harbor is Maddict's internal marketing-analytics pipeline for
location-based advertising campaigns. It records campaign metadata in
BigQuery (`Campaign_Tracker`), builds served and control audience segments,
publishes them to Google Drive and BigQuery, runs scheduled reporting queries
through a Cloud Function, and offers a local Flask operations dashboard.

The repository is mid-modernization. None of that work is on `main` yet, and
it currently spans two diverged branch lines. Read `docs/PROJECT_STATE.md` for
the audited status, and re-audit it (updating its "Last audited" date) when
you change the facts it records.

## 11. Architecture and important directories

| Path | What it is |
|---|---|
| `projects/automation/` | Cloud Function source (`main.py` entry point) and the manual `custom_codename.py` runner. CI deploys **this directory alone** — root-level modules such as `shared/` are not in the deploy artifact |
| `projects/segments/` | Manual segment extraction, split, and publish pipeline (`main.py`, `main_new.py`, `scripts/`) |
| `projects/campaign-tracker/` | Manual campaign-metadata writer (hyphenated; load via `shared/utils/compatibility.py`) |
| `projects/poi/` | Manual POI extraction (IH-036) |
| `ui/` | Flask operations app (`app.py`, Jinja templates with Bootstrap 5.3) |
| `campaign_manager.py` | Campaign registry CLI |
| `shared/config/settings.py` | Additive shared settings. Legacy `variables.py` and `input.py` stay authoritative for a component until its field-level parity is proven |
| `shared/config/environment.py`, `source_allowlist.py`, `output_policy.py` | Phase A safety contracts: imported by no live entry point, **not enforced at runtime**, authorize no cloud testing. Wiring them in is Phase B and needs explicit approval |
| `shared/config/campaigns/`, `shared/models/` | Campaign registry, DB loader, `CampaignConfig` |
| `tests/` | Offline unit tests, fakes, fixtures, parity helpers |
| `docs/` | Audit register, modernization log and spec, architecture plan, project state |
| `features/` | Loop-engineering queue, templates, and per-feature specs and evidence |
| `.claude/agents/`, `.claude/skills/` | Claude Code subagents and loop skills |
| `keys/`, `data/` | Git-ignored local credentials and pipeline data. **Never open `keys/`** |

Target architecture: `docs/architecture-and-test-environment-plan.md`. Build
it only through approved, incremental features.

## 12. Development and validation commands

Setup, from PyPI only:

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

Pin `numpy<2` in that environment until IH-049's pin is integrated into your
branch (`pandas==2.1.1` is ABI-incompatible with numpy 2.x). On this Windows
checkout the system `python` has no pytest, so run tools through
`.venv/Scripts/python.exe` (use `.venv/bin/python` on Linux or macOS). CI uses
plain `python` on Ubuntu with Python 3.12.

| Purpose | Command |
|---|---|
| Full offline test suite (required) | `python -m pytest -q` |
| One test file | `python -m pytest tests/unit/<file>.py -q` |
| Syntax check (exactly what CI runs) | `python -m compileall -q projects shared ui tests campaign_manager.py` |
| `tests/` not re-ignored (must exit 1) | `git check-ignore -q tests/conftest.py` |
| No credentials tracked (must print nothing) | `git ls-files \| grep '^keys/'` |
| Lint / format | **Not configured** |
| Type-check | **Not configured** |
| End-to-end tests | **Not configured** |
| Build | **None.** The Cloud Function deploys source; deploying is prohibited |

Do not introduce a new lint, type-check, or test framework as a side effect of
other work. Propose it as its own feature through `/plan-feature`.
`git diff --check` reports mostly CRLF artifacts on this repository
(`core.autocrlf=true`), so judge its output line by line.

Never run an application entry point as a smoke test (§2).

## 13. Environment variables

| Variable | Read by | Rule |
|---|---|---|
| `INFO_HARBOR_API_TOKEN` | `ui/app.py:54-61` | Bearer token for state-changing routes. Unset means every protected route returns 401 |
| `INFO_HARBOR_FLASK_SECRET_KEY` | `ui/app.py:37-38` | Required; the app refuses to start without it |
| `INFO_HARBOR_ENVIRONMENT` | `shared/config/environment.py:22` | Phase A contract only; no runtime code reads it yet |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google client libraries | Must be empty in tests and CI (`pr-validation.yml`) |

- Never commit, print, log, or place a value in a URL, test, evidence file, or
  served HTML or JavaScript. `.gitignore` already excludes `*.env`, `*.json`,
  `*.key`, `*.pem`, and `keys/`.
- Only `.env.example` files with variable names and safe placeholders may be
  tracked (architecture plan §Decisions). None exists yet.
- The `GOOGLE_CLOUD_PROJECT`, `BIGQUERY_DATASET`, and `API_KEYS_PATH` variables
  in `README.md` are not read by any code.

## 14. Coding conventions

- Confirm the live entry point before editing: duplicate module names do not
  imply duplicate behavior.
- Do not add new `sys.path` mutation or generic same-name imports. Load legacy
  sibling modules by explicit file path under a private alias
  (`importlib.util.spec_from_file_location`), as `projects/automation/main.py`
  and `shared/utils/compatibility.py` do (IH-014, IH-047).
- Keep new configuration additive and typed. Do not silently merge legacy
  values that differ by application.
- Keep cross-domain business code out of catch-all `utils` or `common`
  directories. Generic helpers must be pure and genuinely shared.
- New cloud-facing code must be testable with the offline fakes in
  `tests/fakes/`, and must not construct a real client at import time.
- Neutralize nondeterminism in tests (seed `random`, monkeypatch `datetime`)
  without changing production defaults (§4).
- A test that documents a known defect carries `# BUG: IH-###` and is flipped
  in the commit that fixes it (`docs/modernization-spec.md` §7).
- No bare `except:`, no swallowed failures, no fabricated success responses
  (IH-002, IH-041).
- Match the surrounding file's style and comment density. No repository-wide
  formatter is configured, so do not reformat code you are not changing.

## 15. Security and privacy constraints

- Everything in §2 and §9.
- Never log credentials, tokens, raw device identifiers (DIDs), or sensitive
  query values.
- Treat any value reaching SQL or a Drive query string as untrusted (IH-030).
  Do not add new f-string interpolation of external input.
- Every new or changed state-changing Flask route must keep
  `@require_api_token` and fail closed (IH-025).
- `projects/automation/test_backend_upload.py` (untracked) deletes a
  production table. Never run, import, commit, or delete it without a human
  decision (IH-042).

## 16. Git and branch rules

Extends §3 and §9.

- Branch names: `feature/<slug>`, `fix/<slug>`, `chore/<slug>`. One concern per branch.
- Never use destructive Git commands (`reset --hard`, `clean`, `checkout --`
  on others' work, `stash drop`, `branch -D`, force-push) without explicit,
  scoped human approval.
- Never switch branches while uncommitted work you did not create is present.
- Treat existing uncommitted, untracked, or stashed work as intentional and
  preserve it.
- Committing, pushing, and opening PRs require authorization in the current
  session. Merging to `dev` or `main` is a human action.
- Local-only branches exist (`feature/phase2-integration`). Do not assume a
  local branch is on `origin`, or the reverse.

## 17. Files and behavior that must be preserved

- `.github/workflows/deploy.yml`: unchanged without infrastructure-owner approval.
- `.github/workflows/pr-validation.yml` guardrails, and `tests/conftest.py`'s
  `_block_real_cloud_clients` fixture.
- `.gitignore` must never re-ignore `tests/` (IH-037).
- `projects/automation/` must stay deployable as a self-contained source root.
- Output parity (§4), including every production table, dataset, and Drive path name.
- Existing `docs/code-audit.md` IDs (sequential, never reused) and the
  append-only `docs/modernization-log.md`.
- Historical documents (`docs/refinement-review.md`, `README_NEW.md`,
  `RESTRUCTURE_SUMMARY.md`): mark them outdated or superseded, do not delete them.

## 18. Feature workflow (loop engineering)

```text
/plan-feature → /review-feature spec (PASS required) → HUMAN APPROVAL → /implement-feature
  (build → validate → correct ≤5) → reviewing
  → /review-feature implementation (feature-reviewer) → human_review
  → HUMAN → done
```

Queue: `features/QUEUE.md`. Template: `features/_template/spec.md`. Rules and
states: `features/README.md`.

1. **Planning** (`/plan-feature <slug> <description>`): read this file,
   `docs/PROJECT_STATE.md`, the queue, and the code. Ask only material
   questions. Write `features/<slug>/spec.md` without touching production code.
   Set the queue to `ready` and stop.
2. **Specification review** (`/review-feature spec <slug>`): the
   `feature-reviewer` subagent checks the spec adversarially. A `FAIL` returns
   the feature to `planning`.
3. **Human approval**: a human fills in the spec's Approval section. Nothing
   else counts as approval.
4. **Implementation** (`/implement-feature <slug>`): refuses without a
   recorded spec-review `PASS`, without approval, or with blocking questions.
   Protects pre-existing changes, makes the smallest
   change, runs §12 validation, and corrects root causes for at most five
   unsuccessful cycles **per invocation** before stopping as `blocked`.
   Evidence goes in `features/<slug>/verification/`. When validation passes it
   sets the queue to `reviewing` and stops; it never runs the reviewer, never
   writes an implementation review, and never sets `human_review`.
5. **Independent review** (`/review-feature implementation <slug>`): the only
   step that invokes `feature-reviewer` (fresh context, read-only,
   adversarial), which returns exactly `PASS` or `FAIL`. It records the verdict
   in `features/<slug>/verification/implementation-review-<n>.md`. A `FAIL`
   returns the feature to `building`, with at most three rounds before
   `blocked`.
6. **Human review**: `/review-feature implementation` is the only step that may
   set `human_review`, and only when it has recorded a reviewer `PASS` **and**
   the latest `validation-<n>.md` record passed. A human reviews it, merges
   through the normal PR process, and sets `done`.

## 19. Evidence requirements

- Every claim cites `file:line`, a commit, a test id, or a command with its
  observed output.
- Validation records state the exact command, working directory, Git state,
  exit code, and result. See `features/_template/verification/README.md`.
- Evidence never contains secrets, DIDs, or production data. Save evidence as
  `.md` or `.txt`, because `*.json` and `*.log` are git-ignored.
- Distinguish facts, inferences, and unverified claims. Never report something
  as working because an older document says so.

## 20. Definition of done

A feature is `done` only when **all** of the following are true:

1. Every acceptance criterion in its approved spec is satisfied.
2. The relevant automated checks pass, including `python -m pytest -q` and the CI syntax check.
3. Manual verification is completed where the spec requires it.
4. Verification evidence is recorded under `features/<slug>/verification/`.
5. The independent `feature-reviewer` returned `PASS` on the final state.
6. `git diff` contains no unexplained unrelated changes.
7. `docs/code-audit.md` and `docs/modernization-log.md` are updated per §7.
8. The queue was moved to `human_review`, and then a **human** accepted it and set `done`.

A builder may not mark its own work `done`. No agent may set `done`.

## 21. Scope discipline

- Implement only what the approved spec lists as in scope.
- Record an unrelated defect as a new `docs/code-audit.md` finding or a queue
  `idea` instead of fixing it.
- If the spec turns out to be wrong, stop and return the feature to `planning`
  or `blocked`. Do not redesign silently.

## 22. No automatic merge or deployment

No agent, skill, or subagent merges, pushes to `main` or `dev`, enables
auto-merge, deploys, modifies production credentials, provisions cloud
resources, or runs a destructive migration. Each of those is a human action,
or needs explicit, scoped human approval for that exact action (§9).
