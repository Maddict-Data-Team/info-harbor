# Info-Harbor Refinement Review — Human Checkpoint

This is the human-review checkpoint for the `feature/safety-test-baseline`
refinement work. It summarizes what changed, why, what's left, and what
needs a decision before any further work — including before this branch
is ever merged. See `docs/code-audit.md` (per-finding evidence register)
and `docs/modernization-log.md` (chronological work log) for full detail
behind every summary below.

**Repository:** `https://github.com/Maddict-Data-Team/info-harbor`
**Branch:** `feature/safety-test-baseline`
**State under review:** commit `6b9b9bb92cbfe5e60fd2e627d01c12fdc38fa137`
(this document is itself committed on top of that state, as the final
documentation-only checkpoint — see the repository's own commit log for
this file's exact commit hash).
**Baseline this branch descends from:** `main` at `c0f2e3779c57de37aa48fa48b9edf92e4170b3cb` (unchanged throughout this work).

---

## 1. Verification results

- `feature/safety-test-baseline` is clean and exactly synchronized with
  `origin/feature/safety-test-baseline` (confirmed via `git fetch` +
  `git rev-parse` on both, matching hashes; `git status --porcelain`
  clean aside from one pre-existing, unrelated, untracked local-tooling
  directory).
- `main` confirmed unchanged at `c0f2e3779c57de37aa48fa48b9edf92e4170b3cb`
  throughout this entire effort.
- All 5 pre-existing local stashes confirmed present and untouched (not
  applied, popped, dropped, or modified at any point).
- Full offline test suite: **97 passed**, 0 failed, run with no network
  access and no `keys/` directory required.
- `python -m compileall` over `projects`, `shared`, `ui`, `tests`,
  `campaign_manager.py`: clean, no syntax errors.
- `git check-ignore -v tests/conftest.py` exits 1 (not ignored) —
  confirms the IH-037 `.gitignore` fix still holds and the test suite
  cannot be silently re-excluded.

---

## 2. Commits, grouped by finding

Chronological within each group; all on `feature/safety-test-baseline`,
descending from `main`@`c0f2e37` via `dev`@`810e30b`.

| Finding(s) | Commit | Summary |
|---|---|---|
| IH-007, IH-008 | `374d64a` | Served/control disjointness fix; small-segment crash fix |
| IH-005 | `0632090` | Case-insensitive `queries.ini` section resolution |
| IH-026 | `c28b4a2` | Flask `debug=False`, `host=127.0.0.1` |
| IH-008 | `00517ec` | Correction: bound `get_control()` for undersized eligible pools |
| IH-026 | `0c0997a` | Regression test guarding the debug/host defaults |
| IH-035 | `57a059b` | Declared `pandas` in `projects/automation/requirements.txt` |
| IH-017 | `6f35657` | Keyword-argument the `common_queries` recursive call |
| IH-014 | `7df04a0` | Load campaign-tracker's `main_new.py` via `importlib` |
| IH-015 | `d9b975e` | Missing `sys.path.append` in segments `main_new.py` |
| IH-013 | `49edc31` | Bind `query_HG`'s join predicate to its own alias |
| IH-016 | `d07099e` | Raise a clear error when campaign metadata is empty |
| IH-021 | `fb556e4` | Anchor backend-report file matching to a true prefix |
| IH-012 (partial) | `95dfb9b` | Await tracker `INSERT` jobs (visibility only) |
| IH-009 | `a49ac21` | Truncate raw segment CSVs instead of appending |
| IH-028 (partial) | `5d5990e` | Default `delete_from_drive.py` to dry-run |
| IH-036 (progress) | `71e1566` | Smoke-import test for `projects/poi/main.py` |
| IH-041 | `fd69c53` | `/api/campaigns/add` no longer claims false success |
| IH-004 (characterization only, stop-list) | `8021c53` | Characterization test; not implemented |
| IH-044; IH-025 (risk note); IH-030/012/009 (evidence notes) | `e81c545` | New finding fixed by review; risk escalation and evidence notes on existing findings |
| IH-025, IH-027, IH-046, IH-047 | `6b9b9bb` | Interim bearer-token auth; Flask secret key; automation import fixes |

---

## 3. Findings fixed, partially fixed, or still Open

### Fixed (complete)
IH-005, IH-007, IH-008, IH-009, IH-013, IH-014, IH-015, IH-016, IH-017,
IH-021, IH-025 (interim control — see §5), IH-026, IH-027, IH-035,
IH-041, IH-044, IH-046, IH-047.

### Partially fixed (visibility/default only; residual part needs a decision)
- **IH-012** — a failed tracker `INSERT` now raises instead of being
  silently dropped. The underlying `id`-assignment race is not fixed
  (decision queue).
- **IH-028** — `delete_from_drive.py` now defaults to dry-run. A
  `--confirm` flag and a non-hardcoded folder-id argument are not
  implemented (decision queue).

### Progressed, not fully resolved
- **IH-036** — a smoke-import test now exists; the module's actual
  BigQuery write correctness remains unverified (needs live access).
- **IH-004** — stop-list item; a characterization test proves the defect
  exists; not implemented (decision queue, schema question).

### Still Open (all require a decision, access, or scope this session couldn't grant — see §12 for every one)
IH-001, IH-002, IH-003, IH-006, IH-010, IH-011, IH-018, IH-019, IH-020,
IH-029, IH-030, IH-031, IH-032, IH-034, IH-039, IH-040, IH-042.

---

## 4. Production-output / parity changes

Every fix above was either (a) a documented, pre-approved parity
exception in `docs/modernization-spec.md` §6 (a Critical/High bug fix
where changed output is the intended correction, not a regression), or
(b) a test-only / documentation-only change with no production code
touched. No fix in this checkpoint altered `main`, deployment
configuration, or any BigQuery schema. The specific output changes to be
aware of:

- **IH-007/IH-008**: served CSVs will now correctly exclude control-group
  DIDs; segments under 100,000 raw DIDs no longer crash and instead use a
  proportionally-reduced control group (interim rule, recorded in
  `README.md`, pending placelift-methodology-owner review).
- **IH-005**: a campaign whose `type` is exactly `"Placelift NO BER"` now
  actually runs its reporting queries instead of silently producing
  nothing.
- **IH-009**: a same-day rerun of segment extraction now produces a
  clean file instead of one with a duplicated header and doubled rows.
- **IH-013**: the `query_HG` segment query now runs instead of always
  raising a SQL error (was 100% broken before; no prior "correct" output
  to compare against).
- **IH-021**: backend-report file matching no longer matches on a
  numeric-id substring collision.
- **IH-025**: unauthenticated requests to 5 previously-open write routes
  now receive HTTP 401 instead of executing. This is the intended,
  central effect of the fix.
- **IH-041**: `/api/campaigns/add` now returns `success: false` / HTTP
  501 instead of a fabricated success response.
- All other fixes (IH-014, IH-015, IH-016, IH-017, IH-026, IH-027,
  IH-035, IH-044, IH-046, IH-047) either make a previously-always-broken
  path work correctly for the first time, or change no observable
  behavior on any currently-working path.

---

## 5. Security behavior added — IH-025 and IH-027

**IH-025 (interim bearer-token authentication):**
- Every route in `ui/app.py` was enumerated and classified: 5
  state-changing (protected), 8 read-only (unchanged). Full table in
  `docs/code-audit.md` IH-025.
- Protected routes require an `Authorization: Bearer <token>` header
  matching a server-side-configured token, compared with
  `hmac.compare_digest` (constant-time).
- **Fails closed**: if the expected token isn't configured, every
  protected route rejects every request — there is no "auth optional"
  fallback.
- The 401 response body is fixed and generic; it never reveals whether
  the token is configured, and never echoes any submitted or configured
  token value.
- No CORS headers were added.
- Read-only routes are unchanged.
- **Deliberate, documented consequence**: two of the five protected
  routes are plain browser `<form>` POST targets. Browsers cannot attach
  a custom `Authorization` header to a form submission, so those two
  routes will return 401 to their own existing HTML forms until either
  an operator calls them directly with the header, or the frontend is
  updated to attach it (out of scope for this checkpoint).
- **Not implemented, explicitly out of scope**: CSRF protection, a real
  identity provider (this remains an interim control), per-token
  rotation/revocation, rate limiting.

**IH-027 (Flask secret key):**
- The session-signing key is no longer hardcoded. The application now
  **refuses to start** if the key isn't configured, rather than falling
  back to a hardcoded value or generating a new key on every process
  start (which would have silently invalidated in-flight sessions).

---

## 6. Required runtime environment variables

No example or placeholder values are given below — see §7 for why.

- **`INFO_HARBOR_API_TOKEN`** — the shared bearer token every
  state-changing route in `ui/app.py` requires. Must be a long, random,
  secret value, provisioned by whoever deploys/runs this app. If unset
  or empty, all 5 protected routes reject every request (fail closed —
  this is the safe default, not a malfunction).
- **`INFO_HARBOR_FLASK_SECRET_KEY`** — the Flask session-signing key.
  Must be a long, random, secret value. If unset or empty, the
  application refuses to start.

Both must be supplied through a secure runtime mechanism (a secrets
manager, an orchestrator's secret-injection feature, or an operator's own
shell environment) — never committed to this repository, never
hardcoded, never placed in a URL, log line, or any HTML/JavaScript served
to a browser.

---

## 7. Deployment / runtime steps a human must perform later

These are explicitly **not done** by this checkpoint — no deployment
configuration or CI workflow was touched, per the standing boundary
against deployment changes:

1. Provision `INFO_HARBOR_API_TOKEN` and `INFO_HARBOR_FLASK_SECRET_KEY`
   in whatever environment actually runs `ui/app.py` (this app is
   currently documented as "not deployed anywhere," so this applies
   whenever/if that changes).
2. Decide and implement how operators/other legitimate callers will
   supply the bearer token to the two browser-form routes affected by
   IH-025 (see §5) — no code change was made to the frontend for this.
3. Review and answer every item in the decision queue (§12) before
   considering any of those findings for further work.
4. When ready, request a merge of `feature/safety-test-baseline` into
   `main` — **not done automatically**; this document's author does not
   merge, and has been explicitly instructed not to open or merge a PR
   until told to.

---

## 8. Reviewer findings and how they were resolved

Two read-only review passes (`data-pipeline-reviewer`,
`security-parity-reviewer`) were run over this branch's changes at two
checkpoints, per explicit authorization.

**First pass** (over the first batch of correctness fixes):
- **Confirmed and fixed**: IH-044 (a Cloud-Function-warm-instance
  month-boundary bug in `navigate_and_search_file`'s default argument).
- **Investigated and discarded as a false positive**: a claimed
  `IndexError`/desync in `Write_output_to_files` from excluded segments
  — did not reproduce on direct reading and empirical testing; recorded
  in `docs/code-audit.md` so it isn't re-investigated blind.
- **Risk escalated, not re-implemented**: IH-025 was flagged as having
  gone from a documented-but-latent risk to a live, exploitable one,
  because that session's IH-014 fix made the vulnerable route
  importable/callable for the first time. This directly informed the
  next session prioritizing IH-025 first.
- **Evidence extended**: IH-030's evidence list, and nuance notes on
  IH-012 and IH-009's residual gaps (documented, not re-opened).

**Second pass** (over the IH-025/IH-027 checkpoint, before it was
committed):
- Bearer-token comparison logic, fail-closed behavior for both
  environment variables, absence of token leakage, and the full 13-route
  classification were all independently re-derived by the reviewer from
  the current source and verified clean.
- **One real finding**: fixing IH-046 (a broken import) with a simple
  `sys.path` addition left `projects/automation/main.py`'s internal
  imports vulnerable to silently binding to a same-named but different
  file under `projects/segments/scripts/`, depending on which route was
  hit first in the running process. Reproduced empirically before
  fixing, then fixed as **IH-047** using the same private-alias
  `importlib` loading pattern already established elsewhere in this
  codebase (IH-014). A regression test directly reproduces the original
  collision scenario to guard against it recurring.

---

## 9. Known residual risks

- **IH-025/IH-027 are an interim control, not a final security posture.**
  No CSRF protection, no per-user identity, no token rotation. Treat as
  closing "wide open, no auth at all," not as done.
- **IH-012's `id`-assignment race remains unresolved** (visibility only;
  see decision queue).
- **IH-028's `delete_from_drive.py`** still has a hardcoded folder ID and
  no `--confirm` flag; only the dangerous default was flipped.
- **IH-009's residual gap** (noted by review, not re-opened): the fix
  trades duplicate-row corruption for silent truncation-on-failure if a
  BigQuery fetch is interrupted mid-write; true atomicity would need a
  temp-file-then-rename pattern.
- **The stop-list findings (IH-001, IH-002, IH-004, IH-006) remain
  fully unresolved defects**, some Critical, with real business impact
  already documented in `docs/code-audit.md`. This checkpoint only added
  characterization coverage for IH-004; the others already had
  characterization from the original Phase 1 audit.
- **Everything in the decision queue (§12) is, by definition, an
  outstanding risk** until a human answers it.

---

## 10. Recommended commit-review order

Review in this order — narrowest/lowest-risk first, building up to the
security checkpoint:

1. `374d64a`, `00517ec` (IH-007/IH-008) — read together, same rewrite.
2. `0632090` (IH-005) — self-contained new function + tests.
3. `c28b4a2`, `0c0997a` (IH-026) — trivial config default + its test.
4. `57a059b` (IH-035) — one-line dependency fix.
5. `6f35657` (IH-017) — keyword-argument fix.
6. `7df04a0`, `d9b975e` (IH-014, IH-015) — same importlib pattern, review together.
7. `49edc31` (IH-013) — SQL alias fix.
8. `d07099e` (IH-016) — explicit error on empty result.
9. `fb556e4` (IH-021) — anchored file matching.
10. `95dfb9b`, `a49ac21` (IH-012 partial, IH-009) — segments/tracker write-path fixes.
11. `5d5990e` (IH-028 partial) — dangerous-default flip.
12. `71e1566` (IH-036 progress) — test-only.
13. `fd69c53` (IH-041) — response-honesty fix.
14. `8021c53` (IH-004 characterization) — test-only, stop-list.
15. `e81c545` (IH-044 + risk notes) — read the IH-025 risk-escalation note carefully here.
16. **`6b9b9bb` (IH-025/IH-027/IH-046/IH-047) — review last and most carefully.** This is the security-critical commit: verify the route classification table in `docs/code-audit.md` against `ui/app.py` yourself, and specifically confirm the fail-closed behavior and the IH-047 collision fix before considering this checkpoint reviewed.

---

## 11. Rollback guidance by commit

Every commit on this branch is independently revertible with
`git revert <hash>` in most cases, since each is scoped to one finding
(or a tightly related pair) with its own tests. Two things to know before
reverting anything:

- **IH-008 has two commits** (`374d64a` then corrected by `00517ec`).
  Reverting only `374d64a` without also reverting `00517ec` would leave
  the codebase in an inconsistent partial state — revert both together,
  in reverse chronological order, or neither.
- **`6b9b9bb` (IH-025/IH-027/IH-046/IH-047) is the highest-impact single
  commit to revert**, since it changes route-level behavior (adds
  authentication). Reverting it restores the pre-existing "no auth"
  state on all 5 routes — only do this if a replacement control is going
  in immediately, not as a routine rollback.
- No commit in this branch touches `main`, `.github/workflows/deploy.yml`,
  or any BigQuery schema, so none of these reverts have any production
  blast radius beyond this branch itself, since nothing here has been
  merged or deployed.
- Reverting any commit should be followed by `python -m pytest -q` to
  confirm the resulting state is still internally consistent (a revert
  of a fix commit will also need its accompanying test(s) reverted or
  the suite will fail against the restored old behavior — each commit's
  test file(s) are named after the same finding ID for exactly this
  reason).

---

## 12. Decision queue

Every item below is genuinely blocked — none has a single unambiguous
correct answer this session could safely guess. Ranked by severity.

### IH-001 — Wrong-campaign global override in segments query builder
- **Business impact (plain language):** Running the segments pipeline
  for one campaign can silently pull and publish a *different*
  campaign's audience data under the wrong campaign's name, with no
  error. This is a data-correctness and client-trust risk.
- **Options:** (a) make `build_query` use only its `codename` parameter,
  never the module-level global; (b) redesign the five worker scripts'
  import pattern so they stop each holding an independent, stale copy of
  campaign state.
- **Recommendation:** (a) — smallest fix that directly closes the gap;
  (b) is a larger, valuable but separate refactor.
- **Risk of recommendation:** Requires touching a shared function called
  by multiple worker scripts; needs its own dedicated branch and careful
  regression testing (already has a characterization test to build on).
- **Who decides:** Developer (technical fix), but the business owner
  should be aware given the data-correctness stakes.
- **Changes:** production output (correctness fix, not a schema/deploy/auth change).

### IH-002 — Silent cloud pipeline failure (bare `except` + always-200)
- **Business impact:** When the scheduled reporting job fails for any
  reason, nobody is alerted — the failure is invisible unless someone
  manually reads Cloud Function logs.
- **Options:** (a) minimal — re-raise/return a real error status; (b)
  full — build the proposed `Campaign_Runs` audit-trail table first,
  then make failure handling precise per-campaign.
- **Recommendation:** (b), because a minimal fix without an audit trail
  risks making transient errors newly loud/alarming without giving
  anyone the context to triage them.
- **Risk of recommendation:** Larger scope, a new table, more design
  work before any code lands.
- **Who decides:** Infrastructure owner (on-call/alerting design) and developer.
- **Changes:** production output and (if the `Campaign_Runs` table is
  built) schema. No deployment or auth change.

### IH-003 — Campaign marked "Finished" before reporting succeeds
- **Business impact:** A campaign whose final report fails is still
  marked done, so it's silently excluded from automatic retry (manual
  recovery remains possible today).
- **Options:** tied to IH-002's `Campaign_Runs` design.
- **Recommendation:** Solve together with IH-002, same branch.
- **Risk:** None additional beyond IH-002's own.
- **Who decides:** Infrastructure owner and developer.
- **Changes:** production output; schema if bundled with IH-002.

### IH-004 — Database-loaded campaigns lose segment definitions
- **Business impact:** When campaign config loads from BigQuery (the
  primary path), every campaign silently loses its audience-segment
  list, even where that data exists in the fallback config.
- **Options:** (a) extend the `Campaign_Tracker` schema to store
  segments; (b) merge database-sourced fields with the hardcoded
  fallback instead of replacing the whole registry.
- **Recommendation:** (b) — avoids a schema change, and the fallback
  data already exists.
- **Risk:** Merge-precedence rules need to be spelled out (which source
  wins per field) to avoid a new, different silent-loss bug.
- **Who decides:** Developer, with the methodology/business owner
  confirming which source should win.
- **Changes:** production output. Schema only if option (a) is chosen instead.

### IH-006 — `"Retail Intelligence Dashboard"` type mismatch
- **Business impact:** Retail campaigns using this hardcoded type
  silently produce no reports.
- **Options:** rename the `queries.ini` section to match, or change the
  campaign config's type string to match the section.
- **Recommendation:** No technical preference — this is purely a naming
  decision.
- **Risk:** Low, either direction, as long as it's applied consistently.
- **Who decides:** Whoever owns campaign-type naming conventions (likely
  the methodology owner or whoever maintains `shared/config/campaigns/`).
- **Changes:** production output only.

### IH-010 — `reset_folders()`/`get_raw_segments()` never invoked
- **Business impact:** Without a folder reset between runs, segment data
  from prior campaigns can accumulate and contaminate a new run.
- **Options:** (a) uncomment the calls, making this script run
  end-to-end automatically; (b) leave as an intentional manual/partial
  step and document that clearly instead.
- **Recommendation:** Ask first — the omission looks accidental (the
  script runs every *later* stage) but could reflect an intentional
  operational workflow this session has no visibility into.
- **Risk:** Guessing wrong either way changes real pipeline behavior.
- **Who decides:** Developer/operator who knows how this script is
  actually run today.
- **Changes:** production output (whichever option is chosen).

### IH-011 — Google Drive re-upload creates duplicate files on rerun
- **Business impact:** Rerunning segment publication creates duplicate
  same-named files in the campaign's Drive folder; downstream consumers
  may read the wrong one.
- **Options:** Search-and-replace the existing file before upload, or
  version it. Requires first making `transfer_to_drive.py` accept an
  injectable Drive service (a refactor, not just a fix).
- **Recommendation:** Bundle with IH-012's multi-row-INSERT follow-up
  work, since both need similar dependency-injection groundwork.
- **Risk:** Moderate — touches the live upload path.
- **Who decides:** Developer.
- **Changes:** production output only.

### IH-018/IH-019/IH-020 — Date-window timestamps, `time_interval` sizing, dedupe identity
- **Business impact:** (018) Reporting windows may silently exclude the
  final day's data and are timezone-ambiguous across markets. (019) A
  campaign cannot actually configure its reporting cadence — the window
  is hardcoded regardless of `time_interval`. (020) A dedupe step can
  silently undercount genuinely-duplicate legitimate activity.
- **Options:** Each has a real technical fix, but each also changes
  real report numbers for real campaigns, in ways only the placelift
  methodology owner can validate as correct.
- **Recommendation:** Do not guess; route all three to the methodology
  owner together, since they're all about what a report "should" measure.
- **Risk:** Silent output changes to production reports if implemented
  without sign-off.
- **Who decides:** Placelift methodology owner (boss-level or equivalent
  subject-matter authority), then developer.
- **Changes:** production output; IH-018 also touches `queries.ini` (SQL).

### IH-029 — Inconsistent credential model (key files vs. Secret Manager)
- **Business impact:** Two different trust models coexist; the
  key-file path is weaker and harder to rotate.
- **Options:** Converge everything on Secret Manager.
- **Recommendation:** Agree, but scope as its own dedicated
  infrastructure-hardening branch — this isn't a single-file fix.
- **Risk:** Touches credential-loading code across the UI and segments scripts.
- **Who decides:** Infrastructure owner.
- **Changes:** No production output change; changes how authentication/credentials are sourced.

### IH-030 — Unparameterized SQL and Drive query-string interpolation
- **Business impact:** No query anywhere uses parameterized SQL; a
  campaign name with an apostrophe already breaks a query today, and a
  deliberately crafted value could inject additional clauses.
- **Options:** Full parameterization (BigQuery `ScalarQueryParameter`)
  everywhere, or minimum-viable escaping for Drive query strings only.
- **Recommendation:** Minimum-viable escaping first (fast, low-risk),
  full parameterization as a separate, larger hardening branch.
- **Risk:** Full parameterization touches many files; partial escaping
  is easy to under-scope and miss a call site.
- **Who decides:** Developer, with infrastructure owner sign-off given
  the security angle.
- **Changes:** No production output change if done correctly; security posture only.

### IH-031/IH-032 — Idempotent writes for `{codename}_visitors` and the combined segments table
- **Business impact:** Both tables can accumulate duplicate rows on a
  rerun of an otherwise-successful pipeline step, not just on error.
- **Options:** Dedupe-on-load with a real row identity, or a
  MERGE/upsert pattern.
- **Recommendation:** Design alongside IH-002's `Campaign_Runs` work —
  the audit-trail model and idempotent-write model are closely related.
- **Risk:** Needs a real row-identity scheme decided first.
- **Who decides:** Infrastructure owner and developer.
- **Changes:** production output; possibly schema (new identity column).

### IH-034 — CI deploys to production on every push to `main`, no test gate
- **Business impact:** Nothing currently stops a broken change from
  auto-deploying to the production Cloud Function.
- **Options:** Require the offline test suite (already exists, 97
  tests) to pass before `deploy.yml` runs.
- **Recommendation:** Implement once this branch (or its findings) are
  merged — but explicitly **not attempted this session**, since it's a
  deployment-configuration change, out of bounds by explicit instruction.
- **Risk:** Low technically; the risk is entirely about *who* is
  authorized to change deployment behavior.
- **Who decides:** Infrastructure owner (owns CI/deploy configuration).
- **Changes:** deployment configuration only.

### IH-039 — `aaa` file may indicate repository/production drift
- **Business impact:** Unknown until validated — could mean the
  deployed Cloud Function doesn't match this repository's history.
- **Options:** Compare deployed source (via `gcloud functions
  describe`/logs) against this repo's commit history.
- **Recommendation:** Validate before merging anything to `main` — if
  drift is real, that changes the risk calculus for every other finding.
- **Risk:** None from investigating; the risk is in *not* checking.
- **Who decides:** Whoever has GCP read access (infrastructure owner).
- **Changes:** No change by itself — an investigation, not a fix.

### IH-040 — Unexplained `keys/test-google-sheet.json`
- **Business impact:** Unknown provenance of a local credential file.
- **Options:** Confirm its purpose and remove if unused.
- **Recommendation:** Local hygiene task, low urgency.
- **Risk:** None from asking.
- **Who decides:** Whoever manages this local machine's `keys/` directory.
- **Changes:** No repository change (the file isn't tracked by git).

### IH-042 — Untracked live-credential test script revealed by the `.gitignore` fix
- **Business impact:** A manual smoke-test script with real
  BigQuery/Secret Manager credentials sat silently hidden until this
  session's `.gitignore` fix exposed it.
- **Options:** Commit it under a clearly-separate name/location, or
  delete it, or leave it deliberately untracked.
- **Recommendation:** Someone who knows this script's history should
  decide — it was left completely untouched by this session specifically
  because it touches production credentials.
- **Risk:** None from waiting; risk is in acting on it without knowing
  its purpose.
- **Who decides:** Developer with knowledge of this script's origin.
- **Changes:** No production change either way — a repository-hygiene decision.

### IH-012 (residual) — `id`-assignment race in the campaign-tracker INSERT loop
- **Business impact:** Two countries' rows can compute the same "next
  id" if run close together; visibility is now fixed, the race itself isn't.
- **Options:** Single multi-row `INSERT` per campaign, or a proper
  surrogate key generator.
- **Recommendation:** Single multi-row `INSERT` — smaller change, fixes
  both the race and the id-gap side effect noted during review.
- **Risk:** Changes the exact SQL shape of this insert; needs testing
  against a live-parity check eventually.
- **Who decides:** Developer.
- **Changes:** production output (id values), no schema/deploy/auth change.

### IH-028 (residual) — `delete_from_drive.py`'s `--confirm` flag and folder-id argument
- **Business impact:** The dangerous default is now off, but there's
  still no explicit confirmation step and the folder id is hardcoded.
- **Options:** Add argument parsing (`argparse`) with a required
  `--confirm` flag and a required folder-id argument.
- **Recommendation:** Cheap follow-up, low risk, do whenever convenient.
- **Risk:** Low — this only affects operators running the script directly.
- **Who decides:** Developer.
- **Changes:** No production output change; changes the script's CLI
  interface only.

### IH-036 — `projects/poi/` CI/test integration decision
- **Business impact:** An entire module writes to BigQuery with no test
  coverage of its actual write logic and no CI wiring.
- **Options:** Wire it into CI/tests as a first-class component, or keep
  it an intentionally standalone manual tool.
- **Recommendation:** Ask — this is a scope/ownership question about
  whether `projects/poi/` is meant to be a maintained part of the system.
- **Risk:** None from asking; risk is in guessing its intended status.
- **Who decides:** Whoever owns the POI feature (likely the boss or
  product owner, since this determines maintenance investment).
- **Changes:** No code change from the decision itself; downstream work
  (deeper testing) would not change production output on its own.
