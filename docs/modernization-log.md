# Info-Harbor Modernization Log

Chronological, append-only record of modernization work. Each entry is added
in the **same** branch/PR as the code change it describes. See
`docs/code-audit.md` for the per-finding issue register and `README.md`'s
"Modernization Status" section for a plain-language summary.

---

## 2026-08-20 — `feature/safety-test-baseline` — IH-035 fixed (autonomous refinement continues)

**Goal:** First checkpoint of the continued autonomous refinement pass,
per explicit authorization to proceed through all remaining unblocked
findings without stopping between them.

**Finding fixed:**
- **IH-035** (Low) -- added `pandas==2.1.1` to `projects/automation/requirements.txt`
  (the file Cloud Functions actually installs from). `data_validation.py`
  imports `pandas` but it was undeclared there; latent today (not imported
  by `main.py`), but a deploy-time `ModuleNotFoundError` waiting to happen.
  Pin matches the root `requirements.txt`'s existing pin. Confirmed no
  other imports in `data_validation.py` are similarly undeclared.

**Files changed:** `projects/automation/requirements.txt` (1 line),
`tests/unit/test_automation_requirements.py` (new, 1 test), `docs/code-audit.md`.

**Tests:** focused (1) and full suite both passing:
```
python -m pytest -q
# 56 passed
```

**Parity implications:** None -- adds a missing dependency declaration,
does not change any code path's behavior.

---

## 2026-08-20 — `feature/safety-test-baseline` — IH-017 fixed

**Finding fixed:**
- **IH-017** (Medium) -- `run_pipeline_queries`'s recursive call for
  `"common_queries"` passed `(start_date_q, end_date_q)` positionally into
  slots declared `(end_date_q, start_date_q)`, transposed. Latent (no
  `[Common Queries]` entry in `queries.ini` currently uses either
  placeholder), but would silently invert every date window the moment one
  did. Fixed by switching the whole recursive call to keyword arguments, so
  a future signature reorder can't reintroduce the swap silently.

**Files changed:** `projects/automation/query_orchestrator.py` (1 call
site), `tests/unit/test_automation_build_query.py` (renamed
`TestCommonQueriesDateSwapIsCurrentlyLatentNotActive` ->
`TestCommonQueriesDateSwapFixed`; kept the placeholder-absence guard, added
a test that intercepts the real recursive call and asserts the dates
arrive unswapped), `docs/code-audit.md`.

**Tests:** focused (6) and full suite passing:
```
python -m pytest -q
# 57 passed
```

**Parity implications:** None observable today (the bug was never
triggered by current `queries.ini` content); prevents a future silent
date-window inversion if `[Common Queries]` ever gains a date placeholder.

---

## 2026-08-20 — `feature/safety-test-baseline` — IH-026 regression test added

**Goal:** Close the one gap noted when IH-026 was fixed (no test existed
since it was originally a config default, not a logic defect) with a small
offline regression guard, per explicit request.

**Change:** Added `tests/unit/test_ui_app_safe_defaults.py`. Parses
`ui/app.py`'s source with Python's `ast` module and asserts the `app.run()`
call's `debug` and `host` keyword arguments -- it never imports or runs
`ui/app.py`, so it can't trigger any of the app's own import-time behavior
(campaign registry loading, Flask route registration, etc.) or open a
socket. Protects specifically against `debug=True`/`host='0.0.0.0'` being
silently reintroduced.

**Files changed:**
- `tests/unit/test_ui_app_safe_defaults.py` (new, 1 test)
- `docs/code-audit.md` -- IH-026's "How to reproduce" and "Tests required"
  fields updated to reference the new test.

**Tests:** focused and full suite both run and passing:
```
python -m pytest -q tests/unit/test_ui_app_safe_defaults.py -v
# 1 passed
python -m pytest -q
# 55 passed
```

**Parity implications:** None -- test-only change, no production code
touched.

---

## 2026-08-20 — `feature/safety-test-baseline` — IH-008 review correction

**Goal:** Correct the incomplete IH-008 fix found by independent data-pipeline
and security/parity review. The first fix bounded the 100,000-DID candidate
sample but left `get_control()` requesting the fixed 50,000-DID control size,
so a smaller eligible pool could still raise `ValueError`.

**Business decision:** For fewer than 100,000 eligible DIDs, reduce the control
group proportionally using the existing 50,000-of-100,000 ratio (50%), rounded
to the nearest DID. Keep at least one control DID for a non-empty pool, return
an empty control for an empty pool, and retain the 50,000 cap for larger pools.
The root README records this interim rule for later discussion with the
placelift methodology owner.

**Changes:** `get_control()` now computes a bounded proportional sample size;
the IH-008 tests cover a 50-DID pool producing 25 controls and the empty-pool
boundary; `docs/code-audit.md` now describes the complete fix.

**Parity:** Deliberate, approved correction. Undersized pools now produce both
control and served populations instead of crashing. Large-pool behavior is
unchanged.

---

## 2026-08-20 — `feature/safety-test-baseline` — IH-007 and IH-008 fixed

**Goal:** First Phase 4 correctness fixes, per explicit user authorization to
run an autonomous refinement pass on `feature/safety-test-baseline` in
priority order, starting with IH-007.

**Scope-convention deviation, noted for the record:** `docs/modernization-spec.md`
§4 lists "no pipeline logic changes" as a non-goal specific to
`feature/safety-test-baseline`, and IH-001's recommended correction and this
log's own 2026-08-19 "Next handoff" section both describe Phase 4 fixes as
belonging on a dedicated correctness-fix branch, pending human approval of
this branch first. The user explicitly and repeatedly named
`feature/safety-test-baseline` as the branch for this work in the
2026-08-20 authorization, so these two fixes were made directly on this
branch rather than a new one. Recorded here rather than silently deviating
from the documented plan.

**Findings fixed:**
- **IH-007** (Critical) -- `projects/segments/scripts/split_segments.py:131`:
  `if did not in control:` -> `if did.strip() not in control:`. The served-file
  exclusion check compared a raw line (with trailing `\n`) against a set of
  stripped DIDs, so it could never match; every control DID leaked into
  served output.
- **IH-008** (Critical) -- `projects/segments/scripts/split_segments.py:64-66`:
  `random.sample([...], k=100000)` -> materialize the population first, then
  `random.sample(population, k=min(100000, len(population)))`. Any segment
  file under 100,000 raw DID lines crashed `read_data_folder()` with
  `ValueError`.

Both were introduced by the same `split_segments.py` rewrite found in the
uncommitted `dev` work (committed as `810e30b`), not present at the `main`
baseline.

**Files changed:**
- `projects/segments/scripts/split_segments.py` (2 lines changed, both fixes above)
- `tests/unit/test_split_segments_control.py` -- `TestServedControlOverlapBug`
  flipped to `TestServedControlDisjointness` (asserts disjointness instead of
  documenting the overlap); `TestControlPoolSubsamplingCrash` flipped to
  `TestControlPoolSubsamplingBelowThreshold` (asserts no crash + full DID
  retention instead of documenting the `ValueError`).
- `docs/code-audit.md` -- IH-007 and IH-008 marked Fixed, with fix location,
  reproduction command, and resolution date.

**Tests:** focused (`test_split_segments_control.py`, 5 tests) and full suite
both run and passing:
```
python -m pytest -q
# 50 passed
```

**Parity implications:** Both are Critical bug fixes explicitly listed as
*deliberate exceptions to parity* in `docs/modernization-spec.md` §6 -- output
is expected to change (served CSVs will now correctly exclude control DIDs;
small segments will no longer crash). This is the intended, approved
behavior change, not a regression.

**Not addressed, still open:** the statistical-design question flagged in
IH-008 -- whether capping the control candidate pool at 100,000 per segment
file (vs. sampling from the full population) is itself correct -- is
unresolved and requires input from whoever owns the placelift methodology.

**Next:** continuing to the next unblocked Critical finding per the
documented plan (IH-005, `"Placelift NO BER"` type-normalizer bypass, is the
next self-contained candidate -- see `docs/code-audit.md`).

---

## 2026-08-20 — `feature/safety-test-baseline` — IH-005 fixed; IH-006 deferred

**Goal:** Continue the autonomous refinement pass to the next unblocked
Critical finding after IH-007/IH-008.

**Finding fixed:**
- **IH-005** (Critical) -- added `resolve_section_case_insensitive(config,
  section_name)` to `projects/automation/query_orchestrator.py`, called once
  at the top of `run_pipeline_queries` before any `config.get(pipeline_type,
  ...)`. Resolves a `queries.ini` section case-insensitively when the exact
  case doesn't match (e.g. Campaign_Tracker's `"Placelift NO BER"` vs. the
  real `[Placelift No BER]` section), falling through to the original
  string -- and the original `NoSectionError` -- when no match exists even
  case-insensitively, so unrelated invalid types are not masked.
  `get_metadata()`'s 5-literal normalizer was intentionally left untouched:
  the fix sits at the section-resolution boundary, not the type-string
  boundary, since canonicalizing at write time would mean changing a
  different project's (campaign-tracker's) production write path.

**Finding considered and explicitly deferred:**
- **IH-006** (High) -- `"Retail Intelligence Dashboard"` vs. `[Retail
  Intelligence]` is *not* a case mismatch (case-insensitive comparison does
  not make them equal), so IH-005's fix does not and should not touch it.
  Fixing it means picking a canonical name -- rename the `queries.ini`
  section, or change the campaign config's `type` value -- which is a
  business-naming decision, not a code defect with one correct answer.
  Deferred per the "ambiguous business behavior" stop-condition in this
  session's authorization; left Open, unchanged, pending input from whoever
  owns campaign-type naming.

**Files changed:**
- `projects/automation/query_orchestrator.py` -- new function
  `resolve_section_case_insensitive`; one call site added in
  `run_pipeline_queries`. No other line changed.
- `tests/unit/test_pipeline_type_mapping.py` -- `TestConfirmedPlacementNoBerMismatch`'s
  old BUG-marked end-to-end test replaced with two tests: one proving the
  raw configparser lookup is still case-sensitive (fix is scoped, not a
  global monkeypatch), one proving the resolver finds the correct section.
  Added a guard test in `TestConfirmedUnknownTypeMismatch` proving the
  resolver does not mask a genuinely-absent section.
- `docs/code-audit.md` -- IH-005 marked Fixed with fix location and
  reasoning for what was deliberately left out of scope (the startup-time
  validation half of the original recommended correction, and IH-006).

**Tests:** focused (`test_pipeline_type_mapping.py`, 13 tests, 2 new) and
full suite both run and passing:
```
python -m pytest -q
# 52 passed
```

**Parity implications:** Deliberate parity exception (IH-005 is listed as
one in `docs/modernization-spec.md` §6) -- a campaign whose `type` is
exactly `"Placelift NO BER"` will now actually run its reporting queries
instead of silently producing nothing. No other `pipeline_type` value's
resolution changes (the resolver only activates when the exact-case lookup
already fails).

**Next:** next unblocked Critical/High candidates per `docs/code-audit.md`:
IH-001 (wrong-campaign global override -- larger, touches 5 worker modules'
import-time globals, needs careful scoping) or IH-025/IH-026 (Flask UI
security -- IH-026 is a small, low-ambiguity config default change;
IH-025's authentication mechanism is a larger design choice).

---

## 2026-08-20 — `feature/safety-test-baseline` — IH-026 fixed; refinement pass paused for review

**Goal:** Continue the autonomous refinement pass to the next unblocked
finding after IH-005.

**Finding fixed:**
- **IH-026** (Critical) -- `ui/app.py:401`: `app.run(debug=True,
  host='0.0.0.0', port=5000)` -> `app.run(debug=False, host='127.0.0.1',
  port=5000)`. Single-line config default change, no design ambiguity:
  matches the audit's recommended correction exactly, and the UI is
  documented as a local-only dashboard with no known deployment (`docs/
  modernization-spec.md` §1.5). No test required (configuration, not logic).
  Verified with `python -m compileall -q ui/app.py`; the UI itself was not
  run, per the branch's safety boundary.

**Findings evaluated and explicitly NOT attempted this pass -- all require
either a dedicated branch or a business decision beyond this session's
authority:**
- **IH-001** (Critical) -- the audit's own recommended correction already
  states this "is a pipeline-logic change and is out of scope for
  `feature/safety-test-baseline` -- it belongs in a dedicated
  correctness-fix branch." Also touches import-time global state across 5
  worker modules; larger blast radius than the fixes made so far.
- **IH-002** (Critical) -- fixing the bare `except:`/unconditional-200
  contract requires deciding the Cloud Function's failure-reporting
  semantics (distinguishing "skip this campaign" from "the whole run
  failed"); the audit's own "Tests required" note says this needs the
  pipeline-logic fix designed first, and it's entangled with the
  not-yet-implemented `Campaign_Runs` model (`docs/modernization-spec.md`
  §3, explicitly a future-branch design proposal).
- **IH-004** (Critical) -- one of its two recommended corrections (extend
  the `Campaign_Tracker` schema) is barred outright by this branch's own
  non-goal ("no schema changes"); the other (merge DB-sourced fields with
  the hardcoded fallback) requires a field-by-field precedence decision --
  ambiguous business behavior, not a single correct answer.
- **IH-006** (High) -- see the 2026-08-20 IH-005 entry above; requires
  choosing a canonical name between two existing values, a business
  decision.
- **IH-025** (Critical) and **IH-027** (High) -- authentication mechanism
  and secret-management approach are both design choices (which auth
  scheme; env var vs. Secret Manager, and Secret Manager access is
  explicitly out of bounds for this session regardless).

**Files changed:** `ui/app.py` (1 line), `docs/code-audit.md` (IH-026 ->
Fixed), `docs/modernization-log.md` (this entry).

**Tests:** full suite still passing (no new tests needed for a config-only
change):
```
python -m pytest -q
# 52 passed
```

**Parity implications:** None measurable offline (UI is not exercised by
the test suite); the change only affects the UI's own network exposure
when a human runs it locally.

**Status of this refinement pass:** Pausing here for human review rather
than continuing into IH-001/002/004/006/025/027, all of which hit this
session's stop-conditions (dedicated-branch requirement or ambiguous
business behavior). Four findings fixed and pushed this session: IH-007,
IH-008, IH-005, IH-026 (commits `374d64a`, `0632090`, and this entry's
commit, all on `feature/safety-test-baseline`). See the chat-level
consolidated review package for commit list, test results, and recommended
review order.

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
