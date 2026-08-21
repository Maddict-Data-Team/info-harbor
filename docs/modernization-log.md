# Info-Harbor Modernization Log

Chronological, append-only record of modernization work. Each entry is added
in the **same** branch/PR as the code change it describes. See
`docs/code-audit.md` for the per-finding issue register and `README.md`'s
"Modernization Status" section for a plain-language summary.

---

## 2026-08-21 — `fix/numpy-pandas-compat` — IH-049 fixed

**Finding fixed:**
- **IH-049** (Medium) -- neither `requirements.txt` nor
  `projects/automation/requirements.txt` pinned `numpy`, so `pip install`
  was free to resolve numpy 2.x alongside the pinned `pandas==2.1.1`, which
  is built against numpy 1.x's ABI and fails at `import pandas`. This
  formalizes, as a requirements-file fix, the same `numpy<2` workaround
  `feature/safety-test-baseline`'s log entry already recorded as a local,
  test-venv-only pin (see "Decisions and tradeoffs" further down this
  file). Added `numpy==1.26.4` (the last numpy 1.x release) immediately
  after the `pandas==2.1.1` line in both files. No application code or
  deployment workflow was touched, per explicit scope.

**Files changed:** `requirements.txt`, `projects/automation/requirements.txt`
(1 line added to each), `tests/unit/test_requirements_numpy_pandas_compat.py`
(new, 2 tests, static text checks only), `docs/code-audit.md` (IH-049 added).

**Tests:** focused (2) and full offline suite passing; separately, in a
fresh temporary Python 3.12 virtualenv created **outside this repository**
(never committed, never touched by the offline suite's own `sys.path`/
`conftest.py` guardrails):
- `pip install -r requirements.txt` — clean
- `pip install -r projects/automation/requirements.txt` — clean
- `python -c "import numpy; import pandas"` — succeeds
- `pip check` — no broken requirements
- `python -m pytest -q` (offline suite, run against the temp venv's
  interpreter) and `python -m compileall -q projects shared ui tests
  campaign_manager.py` — both clean

**Parity implications:** None -- dependency-pin-only change. No production
code, deployment workflow, or GCP-facing behavior touched.

**Not done, needs separate authorization:** `projects/automation/requirements.txt`
is not currently part of the deployed Cloud Function artifact
(`--source projects/automation` in `.github/workflows/deploy.yml` does not
include `shared/`, and `projects/automation/variables.py` was **not**
migrated to `shared/config/settings.py` for this reason — see the
packaging decision note prepared alongside this branch). This fix keeps
both requirements files internally consistent but does not itself change
what Cloud Functions installs or resolve that separate packaging question.

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

## 2026-08-20 — `feature/safety-test-baseline` — IH-014 fixed

**Finding fixed:**
- **IH-014** (Medium) -- `projects/campaign-tracker/` uses a hyphen, so
  `from projects.campaign_tracker.main_new import main` could never resolve
  at any of its 4 call sites (`ui/app.py` x3, `campaign_manager.py` x1),
  each wrapped in `try/except Exception`, so every tracker-run action
  failed immediately and silently (a flash message or JSON error, per
  IH-002's sibling swallow pattern for this UI). Fixed by adding
  `load_module_from_path()` + `get_campaign_tracker_main_new()` to
  `shared/utils/compatibility.py`, using the same
  `importlib.util.spec_from_file_location` pattern already established in
  `projects/segments/scripts/*.py`, and replacing all 4 call sites.

**Self-caught bug during this fix:** the first pass used `replace_all` in
`ui/app.py` with a `new_string` indented for the two 12-space call sites;
the third call site (`api_run_all_trackers`, nested inside `for`+`try` at
16 spaces) matched as a substring starting 4 characters into its line,
producing a line with correct total indentation followed by a
second line 4 spaces short -- syntactically an `IndentationError` waiting
to happen, and semantically would have moved the tracker-load call outside
its `try` block, losing per-campaign error isolation. Caught by
`python -m py_compile` before running tests; fixed with a second, precise
edit. Noted here since it's exactly the kind of unintended-change risk
step 9 of the operating loop is meant to catch.

**Files changed:** `shared/utils/compatibility.py` (2 new functions),
`ui/app.py` (3 call sites), `campaign_manager.py` (1 call site),
`tests/unit/test_campaign_tracker_import_path.py` (new, 2 tests),
`docs/code-audit.md`.

**Tests:** focused (2) and full suite passing:
```
python -m pytest -q
# 59 passed
```

**Parity implications:** This makes a previously-always-broken code path
(campaign-tracker execution from the UI/CLI) reachable for the first time.
Whatever `projects/campaign-tracker/main_new.py`'s `main()` actually does
once *called* (not just loaded) is untested and unaudited beyond this
finding's narrow scope -- this fix only proves the module now loads and
`main` is callable; it does not call it (would construct a real BigQuery
client). No test or fix here executes `main()`.

---

## 2026-08-20 — `feature/safety-test-baseline` — IH-015 fixed

**Finding fixed:**
- **IH-015** (Medium) -- `projects/segments/main_new.py` imported its
  worker scripts via dotted paths, but those scripts do their own flat,
  unqualified imports internally (`from variables import *`, `import
  query_orchestrator`), requiring `projects/segments/scripts` on
  `sys.path` -- something `main_new.py` never did, unlike
  `projects/segments/main.py`. Empirically confirmed broken
  (`ModuleNotFoundError: No module named 'query_orchestrator'`) before the
  fix, and confirmed resolved after, using the same venv all other fixes
  on this branch are verified against.

**Fix:** added `sys.path.append(str(scripts_dir))` to `main_new.py`,
mirroring `main.py:11-15`'s existing pattern exactly.

**Files changed:** `projects/segments/main_new.py` (4 lines),
`tests/unit/test_segments_main_new_import.py` (new, 1 test),
`docs/code-audit.md`.

**Tests:** focused (1) and full suite passing:
```
python -m pytest -q
# 60 passed
```

**Parity implications:** Makes a previously-always-broken import path
(the "new" segments entry point) reachable. As with IH-014, this only
proves the module now loads and `main` is callable -- `main()` itself
constructs real BigQuery/Drive clients via `authenticate_get_clients()`
and is neither called by the fix nor by the test.

---

## 2026-08-20 — `feature/safety-test-baseline` — IH-013 fixed

**Finding fixed:**
- **IH-013** (Medium) -- `projects/segments/queries.ini`'s `query_HG`
  declared its source table as alias `HG` but its join predicate
  referenced `ls.Longitude`/`ls.latitude` -- an alias never bound in this
  query (leftover from `query_POI`, a different query earlier in the same
  file). Any campaign using the HG segment type would fail with a live SQL
  error every time. Fixed: `ls.Longitude,ls.latitude` ->
  `HG.Longitude,HG.latitude`.

**Scope note:** this is a `queries.ini` edit, which `docs/modernization-spec.md`
§4 lists under this branch's non-goals. Made under the same explicit
authorization already covering the pipeline-logic-change deviation
(2026-08-20 IH-007/IH-008 entry) -- single correct answer, turns an
always-failing query into a working one, no silent-output-change risk
(the query previously hard-errored on every use, never returned wrong
data).

**Files changed:** `projects/segments/queries.ini` (1 line),
`tests/unit/test_segments_queries_ini.py` (new, 1 test), `docs/code-audit.md`.

**Tests:** focused (1) and full suite passing:
```
python -m pytest -q
# 61 passed
```

**Parity implications:** None measurable offline; the query previously
could not run at all (SQL error), so there is no prior "output" to
compare against. Not exercised by any live BigQuery call in this branch.

---

## 2026-08-20 — `feature/safety-test-baseline` — IH-016 fixed

**Finding fixed:**
- **IH-016** (Low) -- `get_metadata()` relied on Python's loop-variable
  leakage, reading `row.end_date` etc. after the collection loop with no
  check that the loop ran at least once. An empty `Campaign_Tracker`
  result (deleted/mistyped code_name) raised an opaque `NameError`,
  swallowed by IH-002. Fixed: raises `ValueError` with a clear message
  immediately after the loop if `countries` is empty.

**Not implemented:** the recommended correction's second half (validate
that all per-country rows agree on shared fields) -- deciding the
behavior on disagreement is a validation-design question, not a
single-answer fix; left open for a follow-up finding.

**Files changed:** `projects/automation/query_orchestrator.py` (1 check
added), `tests/unit/test_get_metadata_empty_result.py` (new, 1 test),
`docs/code-audit.md`.

**Tests:** focused (1) and full suite passing:
```
python -m pytest -q
# 62 passed
```

**Parity implications:** None for the normal (non-empty) path -- only
changes behavior for an already-broken case (empty result), turning an
opaque crash into a clear one.

---

## 2026-08-20 — `feature/safety-test-baseline` — IH-021 fixed

**Finding fixed:**
- **IH-021** (Medium) -- `search_files_in_folder()` used only a Drive
  `name contains '{file_prefix}'` query with no anchoring, so a
  backend-report id that is a substring of another id (e.g. `1001` inside
  `21001_report.csv`) could match the wrong file. Fixed by extracting
  `_file_name_starts_with_prefix()` and applying it as a Python-side
  post-filter on the query results (Drive's query language itself has no
  anchored "starts with" operator, so the initial query must stay broad).

**Files changed:** `projects/automation/upload_backend.py` (extracted
helper + post-filter), `tests/unit/test_upload_backend_search_files.py`
(new, 2 tests), `docs/code-audit.md`.

**Tests:** focused (2) and full suite passing:
```
python -m pytest -q
# 64 passed
```

**Parity implications:** Deliberate correctness fix -- narrows which
files match a given backend-report prefix to true prefix matches only.
Could change which file(s) `upload_backend.py` picks up for a report id
that previously had a substring collision; no such collision is known to
exist in current data (this is a defect-prevention fix, not a response to
an observed incident).

---

## 2026-08-20 — `feature/safety-test-baseline` — IH-012 partially fixed (visibility only)

**Finding partially fixed:**
- **IH-012** (Medium) -- `projects/campaign-tracker/main.py`'s
  `metadata_placelift()` called `client.query(query)` per country with no
  `.result()`, so a failed `INSERT` was silently fired-and-forgotten. Added
  `.result()` so failures now raise. The `id`-assignment race itself
  (`COALESCE(MAX(id), 0) + 1 + {index}`, independently recomputed per
  country) is **not fixed** -- moving to a single multi-row `INSERT` vs. a
  surrogate key generator is a genuine design choice, added to the
  decision queue rather than guessed.

**Files changed:** `projects/campaign-tracker/main.py` (1 line),
`docs/code-audit.md`.

**Tests:** none added (unchanged from the audit's own assessment -- not
offline-testable without either a live BigQuery table or a larger refactor
to make `create_client()` injectable, out of scope here). Full suite still
passing (no test-affecting change):
```
python -m pytest -q
# 64 passed
```

**Parity implications:** Only changes behavior on the already-broken path
(a failed INSERT) -- from silent to raised. No change to any successful
run's output.

---

## 2026-08-20 — `feature/safety-test-baseline` — IH-009 fixed

**Finding fixed:**
- **IH-009** (High) -- `get_raw_segments()` opened the per-segment raw CSV
  with mode `'a'` and unconditionally wrote a `DID` header on every call.
  A same-day rerun appended a second header and duplicated every device ID
  already fetched. Fixed: `'a'` -> `'w'` (truncate-then-write). Chose this
  over the audit's "fail fast if the file exists" alternative since it
  doesn't introduce new error behavior for the same underlying goal.

**Files changed:** `projects/segments/scripts/get_segments_raw.py` (1
line), `tests/unit/test_get_segments_raw_rerun.py` (new, 1 test),
`docs/code-audit.md`.

**Tests:** focused (1) and full suite passing:
```
python -m pytest -q
# 65 passed
```
The audit had deferred testing this, expecting to need to mock "the
BigQuery row iterator" as a follow-up-branch task -- in practice a single
`monkeypatch.setattr` on `query_orchestrator.run_query_behavior` was
enough, so the test was added now instead of deferred further.

**Parity implications:** Deliberate correctness fix -- a same-day rerun
now produces a clean, correctly-sized raw file instead of one with a
duplicated header and doubled rows. Single (non-rerun) runs are
unaffected.

---

## 2026-08-20 — `feature/safety-test-baseline` — IH-028 partially fixed

**Finding partially fixed:**
- **IH-028** (High) -- `delete_from_drive.py` shipped with `DELETE_MODE =
  True`, so running it with no arguments permanently deletes files from a
  hardcoded Drive folder, no confirmation. Flipped the default to `False`.
  **Not implemented:** an explicit `--yes`/`--confirm` CLI flag, and a
  required (not hardcoded) folder-id argument -- both are real feature
  additions (no argument parsing exists in this script today), added to
  the decision queue.

**Files changed:** `projects/segments/scripts/delete_from_drive.py` (1
line + comment), `tests/unit/test_delete_from_drive_safe_default.py` (new,
1 test, AST-only -- does not import or run the script), `docs/code-audit.md`.

**Tests:** focused (1) and full suite passing:
```
python -m pytest -q
# 66 passed
```

**Parity implications:** N/A -- this script was never run in this branch's
work and still isn't; the fix changes what happens if a human runs it with
no arguments in the future (does nothing instead of deleting), not any
currently-observed behavior.

---

## 2026-08-20 — `feature/safety-test-baseline` — IH-036 smoke-import test added

**Progress on IH-036** (Medium, Needs Validation, unchanged overall status)
-- added `tests/unit/test_poi_main_import.py`, confirming
`projects/poi/main.py` imports cleanly and exposes its 8 documented
functions, per the audit's own suggested first step. Whether `projects/poi/`
should be wired into CI/tests as a first-class component, or remain an
intentionally standalone manual tool, is **not decided** -- added to the
decision queue. The module's actual BigQuery write correctness remains
unvalidated (would require live credentials), so IH-036 stays Needs
Validation rather than moving to Fixed.

**Files changed:** `tests/unit/test_poi_main_import.py` (new, 1 test),
`docs/code-audit.md`.

**Tests:** full suite passing:
```
python -m pytest -q
# 67 passed
```

**Parity implications:** None -- test-only change.

---

## 2026-08-20 — `feature/safety-test-baseline` — IH-041 fixed

**Finding fixed:**
- **IH-041** (Low) -- `/api/campaigns/add` validated the submitted
  campaign, then returned `{'success': True, ...}` despite an explicit
  `# TODO: Implement actual database save` immediately above it -- nothing
  was ever persisted. Took the "make the stub explicit" option (not
  "implement persistence", which is a production-write feature addition,
  out of scope): now returns `success: False`, an explanatory `error`, HTTP
  501, and `campaign.persisted: False`. Confirmed the existing frontend
  handler already branches on `data.success` and surfaces `data.error`, so
  no template change was needed.

**Files changed:** `ui/app.py` (1 route's response), `tests/unit/test_ui_add_campaign_response.py`
(new, 1 test, AST-based), `docs/code-audit.md`.

**Tests:** focused (1) and full suite passing:
```
python -m pytest -q
# 68 passed
```

**Parity implications:** Changes this route's HTTP status and response
shape on every call (previously always "successful," now always explicit
about not persisting). No UI/CLI/automation code path other than this one
Flask route is affected.

---

## 2026-08-20 — `feature/safety-test-baseline` — IH-004 characterization test added (stop-list, not fixed)

**Read-only investigation of a stop-list finding**, per explicit
authorization to characterize (but not fix) IH-001/002/004/006/025/027.

**IH-004** (Critical) -- added `tests/unit/test_database_loader_segments_characterization.py`,
calling the real, pure `create_campaign_config_from_db()` with a
hand-built `db_data` dict (no BigQuery). Confirms `segments`,
`custom_segments`, and `excluded_segments` are unconditionally empty
regardless of input -- including when `has_segments=1` explicitly says the
campaign should have segments, a direct contradiction within the returned
`CampaignConfig` itself. **Not fixed** -- remains on the stop-list; see the
consolidated decision queue for the two correction options (extend schema
vs. merge with hardcoded fallback) and a recommendation.

**Files changed:** `tests/unit/test_database_loader_segments_characterization.py`
(new, 1 test), `docs/code-audit.md`.

**Tests:** full suite passing:
```
python -m pytest -q
# 69 passed
```

**Parity implications:** None -- test-only change, no production code
touched.

---

## 2026-08-20 — `feature/safety-test-baseline` — automated review pass: IH-044 fixed, IH-025 escalated, one false positive investigated

**Goal:** Run the read-only `data-pipeline-reviewer` and `security-parity-reviewer`
sub-agents against this session's diff (`3be3697..HEAD` at the time),
per explicit authorization ("run the repository's read-only data-pipeline
and security/parity reviewers at sensible batch boundaries... correct
clear reviewer findings within the authorized scope").

**New finding fixed:**
- **IH-044** (High) -- `projects/automation/upload_backend.py`'s
  `navigate_and_search_file(..., month_name=datetime.now().strftime("%B"))`
  evaluates its default argument once, at module-import time, not per
  call. On a warm Cloud Function instance reused across a month boundary,
  every call omitting `month_name` (the primary call site) keeps
  searching the *previous* month's Drive folder indefinitely, silently,
  until the next cold start. Fixed: default changed to `None`, with the
  real computation moved inside the function body. Found by the
  data-pipeline-reviewer, independently verified against the actual
  source (not just the review's prose) before fixing.

**Existing finding's severity/urgency updated (not re-implemented):**
- **IH-025** (Critical, still Open) -- the security-parity-reviewer
  flagged that this session's IH-014 fix (making
  `projects/campaign-tracker/main_new.py` importable) reactivates
  `/api/run-all-trackers` and the other tracker-run routes in `ui/app.py`
  -- previously always failing with `ModuleNotFoundError`, now capable of
  a real, unauthenticated, no-CSRF BigQuery write across every campaign in
  the registry. IH-025's own text already anticipated this exact route's
  blast radius, but written while the import was still broken (latent,
  not live). Updated the finding to flag it as now live-exploitable and
  recommend prioritizing it. IH-014 itself was not changed -- it's
  correct and narrowly scoped; this is a risk-profile note, not a defect
  in that fix.

**Existing finding's evidence extended:**
- **IH-030** (Open) -- added `projects/campaign-tracker/main_new.py:73-102`
  (same unparameterized-`INSERT` pattern as the already-listed `main.py`)
  to the evidence list, since IH-014 makes this file reachable for the
  first time.

**Existing findings' write-ups extended with reviewer-found nuance (not
re-opened, not re-implemented):**
- **IH-012** -- noted that this session's `.result()` addition serializes
  the per-country loop, turning the unfixed `id`-offset formula into a
  growing-gap pattern instead of a collision risk, and that a mid-loop
  failure now stops immediately with earlier countries already committed.
  Reinforces the existing decision-queue recommendation (single multi-row
  `INSERT`); doesn't change it.
- **IH-009** -- noted that `'w'` mode trades duplicate-row corruption
  (fixed) for silent truncation-on-mid-fetch-failure (pre-existing, not
  introduced by this fix), and that the script's own direct
  `__main__` entry point doesn't call `reset_folders()` first either.

**Reviewer finding investigated and found to be a false positive (no
finding opened, no code changed):** the data-pipeline-reviewer also
reported that `Write_output_to_files` (`split_segments.py`) would desync
`names[i]` from the file being written when a segment is excluded. Reading
the actual code shows `read_data_folder` appends to `names` *before* its
exclusion check, so `names` has one entry per country-matching file
regardless of exclusion status, staying in lockstep with the second loop's
own unfiltered iteration by construction. Verified empirically with a
3-file/1-excluded reproduction (no `IndexError`, correct per-segment
content) before discarding the finding. A refactor attempted while
investigating this (extracting a shared `_is_excluded` helper) was
reverted (`git checkout --`) once the underlying claim didn't hold, to
keep this branch's diff limited to actual fixes. Recorded in
`docs/code-audit.md` so a future reader doesn't re-investigate the same
non-issue from the review's prose alone.

**Files changed:** `projects/automation/upload_backend.py` (IH-044 fix),
`tests/unit/test_upload_backend_navigate_month.py` (new, 1 test),
`docs/code-audit.md` (new IH-044 entry, IH-025/IH-030/IH-012/IH-009
updates, false-positive note).

**Tests:** focused (1) and full suite passing:
```
python -m pytest -q
# 70 passed
```

**Parity implications:** IH-044's fix changes `navigate_and_search_file`'s
behavior only when the process is warm across a month boundary and the
caller omits `month_name` -- the common case (cold start, or within the
same month) is unaffected.

---

## 2026-08-20 — `feature/safety-test-baseline` — IH-025 (interim bearer-token auth) and IH-027 (Flask secret key) fixed; IH-046 fixed

**Goal:** Address IH-025 (Critical, previously top of the decision queue,
escalated by the prior checkpoint's security review) as the highest-priority
task, per an explicit, detailed, user-approved interim authentication
design. IH-027 folded in as tightly related (same file, same category of
Flask-security config).

**Route enumeration and classification (done before implementation, per
instruction):** all 13 routes in `ui/app.py` read and classified --
5 state-changing (protected), 8 read-only (unchanged). Full table recorded
in `docs/code-audit.md` IH-025. One judgment call flagged explicitly:
`/api/refresh` is a POST route but performs no write of any kind (only
re-reads live campaign data), classified read-only and locked in by a
dedicated test so it isn't later assumed to be an oversight.

**IH-025 fixed (interim control):**
- `require_api_token` decorator + `_get_expected_api_token()` added to
  `ui/app.py`, reading `INFO_HARBOR_API_TOKEN` fresh per request (not
  cached at import), comparing via `hmac.compare_digest`, failing closed
  (empty/unset env var -> every protected route always 401, never "auth
  optional"), returning a fixed generic JSON 401 that never reveals
  whether the env var exists or echoes any token value.
- Applied to `run_campaign_action`, `api_run_campaign_action`,
  `api_run_all_trackers`, `api_add_campaign`, `run_automation`.
- No CORS added. No production route was run or accessed with real
  credentials during implementation or testing.
- **Known, deliberate consequence:** `run_campaign_action` and
  `run_automation` are plain browser-`<form>` POST targets; browsers
  cannot attach a custom `Authorization` header to a form submit, so
  these two routes are now unreachable via their existing HTML forms
  until a caller (curl, an operator tool, or an updated frontend)
  supplies the token explicitly. Recorded as intentional, not
  accidental breakage -- the frontend itself was not modified (out of
  scope for this backend interim control).
- Not implemented (explicitly out of scope, noted in the finding): CSRF
  protection, a real identity provider, per-token rotation/revocation,
  rate limiting.

**IH-027 fixed:** `app.secret_key` now reads `INFO_HARBOR_FLASK_SECRET_KEY`;
refuses to start (`RuntimeError` at import) if unset or empty, rather than
falling back to the old hardcoded literal or generating a random key per
process start (this app's `flash()` messages ride on the Flask session
cookie, so a missing key isn't survivable either way -- fail loud, not
silent).

**IH-046 fixed (found while preparing tests for this checkpoint, same
class as IH-014/IH-015):** `projects/automation/main.py` -- the module
`ui/app.py`'s `/automation` route imports -- had the same missing-`sys.path`
defect as IH-015: `import projects.automation.main` raised
`ModuleNotFoundError: No module named 'upload_backend'`. This meant the
`/automation` route (now newly protected) had never actually worked.
Fixed with the same one-line pattern as IH-015.

**Files changed:** `ui/app.py` (auth decorator, secret-key loading, 5
route decorators), `projects/automation/main.py` (IH-046 sys.path fix),
`tests/unit/test_ui_app_auth.py` (new, 24 tests), `tests/unit/test_automation_main_import.py`
(new, 1 test), `docs/code-audit.md` (IH-025 rewritten with route table,
IH-027 updated, new IH-046 entry), `README.md` (new environment-variable
note).

**Tests:** 24 new auth tests (every protected route x {no token, wrong
token, valid token}, with the underlying operation mocked and asserted
never-called / called accordingly; fail-closed behavior for both missing
and empty `INFO_HARBOR_API_TOKEN`; a guard test that fails if a future
write-method route isn't classified as protected or read-only) + 3 new
IH-027 tests + 3 import tests (IH-045/IH-046/IH-047, one of which
directly reproduces the collision the reviewer found), all offline, no
credentials, no network -- every dangerous call in these tests is mocked
before the request reaches it. Full suite:
```
python -m pytest -q
# 97 passed
```

**Reviewer pass:** `security-parity-reviewer` run over this checkpoint's
diff (pre-commit) only, per instruction. Verified clean: bearer-token
comparison logic (no bypass via casing/prefix/empty-string edge cases),
fail-closed behavior for both env vars, no token leakage anywhere, and
the full 13-route classification (independently re-derived by the
reviewer from the current route bodies, not taken on trust). One real
finding: IH-046's `sys.path`-only fix left `projects/automation/main.py`'s
flat imports order-dependent against `projects/segments/scripts/`'s
same-named `query_orchestrator.py`/`variables.py` -- reproduced
empirically, then fixed as **IH-047** (High): `main.py`,
`query_orchestrator.py`, and `upload_backend.py` now all load their local
dependencies via `importlib.util.spec_from_file_location` under private
aliases, matching the pattern already used by
`projects/segments/scripts/*.py` and IH-014's `get_campaign_tracker_main_new()`.
`tests/unit/test_automation_main_import.py` extended from 1 test to 3,
including a direct reproduction of the collision scenario.

**Files changed (final, after the reviewer pass):** all of the above,
plus `projects/automation/query_orchestrator.py`, `projects/automation/upload_backend.py`
(IH-047).

**Parity implications:** Behavior change is intentional and documented:
unauthenticated requests to the 5 protected routes now get 401 instead of
executing (this is the entire point of the fix). Read-only routes: zero
change. `run_campaign_action`/`run_automation`'s existing HTML forms will
now get a 401 JSON response until token support is added to the frontend
or these are called with the header directly -- documented above and in
`docs/code-audit.md`, not silently introduced.

**Decision-queue status:** IH-025 and IH-027 removed from the queue
(fixed). All other queue items unchanged; continuing to remaining
unblocked findings after this checkpoint per instruction.

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
