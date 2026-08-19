# Info-Harbor Modernization Log

Chronological, append-only record of modernization work. Each entry is added
in the **same** branch/PR as the code change it describes. See
`docs/code-audit.md` for the per-finding issue register and `README.md`'s
"Modernization Status" section for a plain-language summary.

---

## 2026-08-19 — `feature/safety-test-baseline`

**Goal:** Establish an offline, credential-free testing foundation and a
complete, evidence-backed audit register for the Info-Harbor codebase,
without changing any production pipeline behavior. Requested baseline was
branch `main` at commit `c0f2e3779c57de37aa48fa48b9edf92e4170b3cb`.

### Baseline verification (before any change)

- The working folder available at session start (`info-harbor-main`) was an
  **extracted archive with no `.git` directory** — not a usable clone.
- A real clone existed at a sibling path (`../info-harbor`), on branch `dev`
  at commit `296a1576ab67b43e6d08c4bf3ec9fb44922ee162` — 5 commits ahead of
  the requested `main` baseline — with **7 uncommitted, modified files**
  (`projects/campaign-tracker/input.py`, `projects/poi/input.py`,
  `projects/segments/input.py`, `projects/segments/main.py`,
  `projects/segments/scripts/delete_from_drive.py`,
  `projects/segments/scripts/push_to_bq.py`,
  `projects/segments/scripts/transfer_to_drive.py`).
- `main` and `origin/main` in that clone both resolved to exactly
  `c0f2e3779c57de37aa48fa48b9edf92e4170b3cb`, confirming the requested
  baseline is real and reachable, just not what was checked out.
- The user redirected: work from `dev` (their own prior work), never commit
  to `main` (it auto-deploys to production). The 7 uncommitted files were
  the user's own prior work-in-progress and were preserved, not discarded.

**Decision:** committed the 7 modified files to `dev` locally (commit
`810e30b5451e962bf7524bf8f22cb341322dda87`, message describing them as
unreviewed WIP preserved from the session start) — **not pushed** — then
created `feature/safety-test-baseline` from that commit.

**Audit re-grounding:** a prior audit of `main`@`c0f2e37` existed from an
earlier session. Before reusing any of it, diffed `main` against this
branch's actual tip: **21 files, ~2,700 lines changed**, including a new
`projects/poi/` module. Every finding below was re-verified against this
branch's real, current file content and line numbers — nothing was carried
over from the earlier `main` audit without re-checking.

### Findings addressed by ID

All 41 findings in `docs/code-audit.md` were investigated and documented in
this branch. Of those:

- **Fixed (already, prior to this branch's own work — recorded for
  visibility):** IH-022 (stale external table reuse in `upload_backend.py`),
  IH-023 (`segments/main.py` `NameError`), IH-024 (`push_to_bq.py` staging
  table conflict-swallow), IH-033 (O(lines) redundant Drive upload calls).
  These were present at the `main` baseline and resolved somewhere between
  `main` and the `dev` work this branch started from.
- **Fixed (by this branch's own work):** IH-037 (`.gitignore`'s `test*`
  pattern blocking any test suite), IH-038 (`projects/poi/` undocumented).
- **New findings, not present at the `main` baseline:** IH-007 (served/
  control disjointness broken by a newline mismatch) and IH-008 (control-pool
  subsampling crash risk), both introduced by the `split_segments.py`
  rewrite found in the uncommitted `dev` work. Both are Critical.
- **Corrected from the earlier `main`-only audit, per explicit instruction:**
  - IH-005 (`"Placelift NO BER"`): re-traced through `get_metadata()` with
    the exact case supplied (`code_name=113`, `type="Placelift NO BER"`,
    `backend_report=0`, `segments=1`). Confirmed **Open** — the type string
    bypasses the five-literal normalizer and does not match the
    case-sensitive `[Placelift No BER]` section. Not marked fixed or
    refuted without this exact reproduction.
  - IH-003 (premature `Finished` status): reframed. A `Finished` campaign
    is **not** unrecoverable — `custom_codename.py` selects by `code_name`
    with no status filter, so manual reruns remain possible. The corrected,
    accurate risk set is: automatic retry is lost, manual recovery is
    unaudited, and manual reruns are not idempotent (can duplicate appended
    data or reuse stale intermediate state).
  - IH-039 (the `aaa` file): downgraded from "evidence of drift" to
    "possible indicator, Needs Validation" — it is a stray log whose content
    doesn't match anything in this repo's source, but that alone does not
    prove the deployed Cloud Function differs from this history; resolving
    it requires GCP read access this session did not have.
- **All remaining findings** were confirmed with exact `file:line` evidence
  against this branch's current content (see `docs/code-audit.md` for the
  full list): IH-001, 002, 004, 006, 009–021, 025–032, 034–036, 040, 041.

### Files or components changed

- `.gitignore` — replaced the blanket `test*` pattern with narrow,
  non-blocking test-artifact patterns (`.pytest_cache/`, `.coverage`,
  `htmlcov/`, `tests-output/`) plus a `.venv/` entry.
- `tests/` (new) — `conftest.py`, `unit/` (7 files), `fakes/`
  (`fake_bigquery.py`, `fake_drive.py`), `fixtures/`
  (`campaign_metadata.py`), `parity/` (`manifest.py` +
  `test_manifest_helpers.py`).
- `pytest.ini`, `requirements-dev.txt` (new).
- `.github/workflows/pr-validation.yml` (new) — offline, non-deploying CI.
  `.github/workflows/deploy.yml` was **not** modified or removed.
- `AGENTS.md`, `CLAUDE.md` (new).
- `docs/modernization-spec.md`, `docs/code-audit.md`,
  `docs/modernization-log.md` (this file) (new).
- `README.md` — added "Modernization Status" section.
- `.claude/agents/repository-mapper.md`,
  `.claude/agents/data-pipeline-reviewer.md`,
  `.claude/agents/security-parity-reviewer.md` (new, read-only definitions).
- Local-only, not committed: `.venv/` (test tooling virtualenv, gitignored).

**No file under `projects/`, `shared/`, `ui/`, or `campaign_manager.py` was
modified.**

### Tests added or executed

50 tests, all offline, all passing:

```
python -m pytest -q
# 50 passed in ~1.1s
```

Breakdown: `test_pipeline_type_mapping.py` (11 — IH-005/IH-006, including the
exact `code_name=113` reproduction), `test_get_run_dates.py` (5),
`test_automation_build_query.py` (5, including the IH-017 regression guard),
`test_segments_wrong_campaign_global.py` (2 — IH-001), `test_split_segments_control.py`
(5 — seeded-RNG determinism, IH-007, IH-008), `test_campaign_config.py` (9),
`test_upload_backend_compare_columns.py` (4), `test_manifest_helpers.py` (9).

Static checks run: `python -m compileall -q projects shared ui tests
campaign_manager.py` (syntax-only, all files compile);
`git check-ignore -v tests/conftest.py` (confirms `tests/` is no longer
gitignored).

### Parity evidence

Not applicable in the sense of "before vs. after a refactor" — no
pipeline-logic code was changed this branch. What *is* established: every
Critical/High finding now has a test that reproduces it against the real,
unmodified production function (not a reimplementation), so any future fix's
parity claim can be checked by watching that specific test flip from
documenting the bug to asserting the fix.

### Decisions and tradeoffs

- Chose to **commit** (not stash, not discard) the user's uncommitted `dev`
  work, since it was clearly intentional in-progress work (key-path
  resolution fixes, a Drive-upload rewrite) rather than scratch output.
- Chose to seed Python's shared `random` module from within tests rather
  than add an `rng=` parameter to `split_segments.get_control` — the latter
  would be a production code change, out of scope for this branch, even
  though it is a small one. This is flagged as a good first task for the
  Phase 4 correctness-fix work in `docs/modernization-spec.md`.
- Chose to install the real `google-cloud-*`/`pandas`/`tqdm`/`flask`/
  `oauth2client`/`pydrive2` packages into a local test-only virtualenv
  rather than mocking imports, so tests exercise real production modules
  end-to-end up to (but never including) an actual network call. Required
  pinning `numpy<2` to resolve an ABI mismatch with the repo's pinned
  `pandas==2.1.1`.
- Discovered and fixed a **test-harness-only** bug during development: an
  early version of `tests/conftest.py` added all four `projects/*`
  directories to `sys.path` simultaneously, which caused
  `projects/campaign-tracker/input.py` (no `code_name` attribute) to
  shadow `projects/segments/input.py` (has `code_name`) when segments
  modules did `from input import *`. Fixed by making the autouse fixture
  add only `REPO_ROOT`, and having each test load the specific file it
  needs via `importlib.util`, mirroring exactly how the real entry points
  isolate their own `sys.path`. This was never a production bug — it never
  existed outside the test process — but is recorded here since it directly
  shaped `tests/conftest.py`'s final design.

### Discovery made during validation

Running `git status` after the `.gitignore` fix (IH-037) revealed a
previously-hidden, **untracked** file that the old blanket `test*` pattern
had been silently excluding: `projects/automation/test_backend_upload.py`
(161 lines) -- a manual smoke-test script for `upload_backend.py` that
authenticates directly with real BigQuery and Secret Manager credentials.
It was not created by this branch, was never run, and is left completely
untouched (not committed, not modified, not deleted) pending a human
decision — see `docs/code-audit.md` IH-042. This is concrete, first-hand
evidence of the risk IH-037 described in the abstract.

### Known limitations

- End-to-end segments-stage parity is not measurable until IH-001 is fixed
  (see `docs/modernization-spec.md` §6, "Known current gap").
- `docs/code-audit.md` IH-039 (the `aaa` file) and IH-040 (an unexplained
  `keys/test-google-sheet.json`) remain Needs Validation — both require
  access this session did not have (GCP read access, and local file
  provenance knowledge respectively).
- `projects/poi/` (IH-036) was documented but not deeply tested; it has no
  tests and is not wired into CI.
- The parity manifest helpers (`tests/parity/manifest.py`) are tested in
  isolation but not yet wired against real fixture-driven end-to-end runs —
  that requires the pipeline-logic refactor work this branch explicitly
  does not do.

### Rollback considerations

This branch adds new files and modifies exactly one existing file
(`.gitignore`, additive only — no removed patterns except the blanket
`test*` line, which was actively harmful). Reverting this branch is a clean
`git revert` with no risk to production: nothing under `projects/`, `shared/`,
`ui/`, or `campaign_manager.py` was touched, and `.github/workflows/deploy.yml`
is untouched. `feature/safety-test-baseline` was never merged to `main` or
`dev` as part of this work — it is presented for review first.

### Next handoff

Human review and approval of this branch is required before any further
work. Once approved, the recommended next branch is Phase 2 from
`docs/modernization-spec.md` (config unification) or a first Phase 4
correctness fix for a single Critical finding (IH-007 is the smallest,
most self-contained starting point: one file, one clear fix, an existing
regression test to flip). Do not begin either without explicit approval —
see `AGENTS.md` §9.
