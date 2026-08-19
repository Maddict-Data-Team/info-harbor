# Info-Harbor Modernization Specification

This document describes the current system, the target architecture, and the
contract any refactor must satisfy. For the detailed, per-defect evidence
behind every claim here, see `docs/code-audit.md`. For the chronological
record of work, see `docs/modernization-log.md`.

**Baseline for this document:** `feature/safety-test-baseline`, branched from
`dev` at `810e30b5451e962bf7524bf8f22cb341322dda87`, itself descended from
`main` at `c0f2e3779c57de37aa48fa48b9edf92e4170b3cb`.

---

## 1. Current workflow

Info-Harbor runs a marketing-analytics pipeline with **four** source folders
under `projects/` (three original stages, plus one added on `dev` — see §1.4).

### 1.1 Campaign metadata (`projects/campaign-tracker/`)

A one-shot, manually-run script. `main.py` reads a hand-edited `input.py`
(campaign name, countries, dates, type, backend report ids, time interval,
segment flag), queries `MAX(code_name)` from `Campaign_Tracker`, increments
it, and inserts one row **per country** with `status = 'Pre-Validation'`.
Not deployed anywhere; run manually by whoever is launching a campaign.
A newer `main_new.py` exists that reads from `shared/config/campaigns/` (the
`CampaignConfig` model) instead of `input.py`, but it currently fails at
runtime (`docs/code-audit.md` IH-014).

### 1.2 Segment extraction and publication (`projects/segments/`)

Given a campaign's countries and audience segment list:

1. `get_raw_segments()` queries BigQuery per segment/country and writes raw
   device-id (DID) CSVs to `data/raw/`.
2. `split_segments.split_files()` draws a random control sample from the
   combined pool of raw DIDs and writes `data/controlled/` (the control
   group) and `data/served/` (each segment minus the control group).
3. `transfer_to_drive.transfer_files_to_drive()` uploads every CSV under
   `data/` (excluding `raw/`) to a `Year/Quarter/CampaignName` folder in
   Google Drive.
4. `push_to_bq.run_push_to_bq()` creates a BigQuery external table per
   uploaded Drive file, inserts each into a combined
   `{code_name}_Segments` table (tagging served vs. controlled), then drops
   the external staging table.
5. `create_be_table.create_BER_Table()` creates an empty Back-End-Reports
   table for the campaign, to be populated later by automation.

Not deployed anywhere; run manually, and requires the process's current
working directory to be the repository root (several paths are hardcoded
relative — see `docs/code-audit.md` IH-010).

### 1.3 Scheduled and manual automation (`projects/automation/`)

This is the **only** component deployed by CI
(`.github/workflows/deploy.yml`, to Cloud Function `ih-cf-executor`).

**Scheduled path — `main.py` (Cloud Function HTTP entry point):**
1. `q_update_status` — a single `UPDATE` that transitions every non-terminal
   campaign's status based on today's date relative to `start_date`/`end_date`.
2. `q_select_active_interval` — selects every row that is either `Active`
   with its `time_interval` due, or in `Completion Period`.
3. For each selected row: if it has a nonzero `backend_report`, attempt to
   pull this period's backend report from Drive into BigQuery
   (`upload_backend.backend_processing`); if the row is in `Completion
   Period`, mark it `Finished` (**before** the reporting step below runs —
   `docs/code-audit.md` IH-003).
4. For each unique `code_name` touched: `query_orchestrator.run_by_codename`
   resolves the campaign's `type` to a `queries.ini` section, computes a date
   window, and runs that section's queries into `Back_End_Footfall`.
5. Always returns HTTP 200, regardless of what happened above
   (`docs/code-audit.md` IH-002).

**Manual path — `custom_codename.py` (CLI, via `make custom <code>`):**
Takes one `code_name` directly (no status filter), and runs the same backend
upload + `run_by_codename` reporting steps for it. **This is not the same
code path as the scheduled one** — it does not run `q_update_status`, it does
not check the BER-upload return value before proceeding, and it has no
`try/except` around the per-campaign work (so a failure here raises visibly
rather than being swallowed). See §3 for a proposed unification.

### 1.4 POI extraction (`projects/poi/`) — new, undocumented prior to this branch

Added on `dev` (commit `8981f83`, after the `main` baseline). A standalone
module with its own `main.py`/`input.py`/`variables.py`, following the same
legacy flat-import pattern as the rest of the repository. It writes points-of-
interest data to its own BigQuery table set. **Not referenced by any other
part of the system** and not deployed by CI — confirmed by a repository-wide
search finding zero references to `projects.poi`/`projects/poi` outside the
directory itself. Its correctness has not been deeply audited; see
`docs/code-audit.md` IH-036 (Needs Validation).

### 1.5 The Flask UI (`ui/`)

Not deployed anywhere; a local dashboard over the campaign registry, with
several write-capable POST routes (run tracker, run segments, run automation,
add campaign, run trackers for *all* campaigns in one request). Currently has
no authentication or CSRF protection — see `docs/code-audit.md` IH-025.

---

## 2. `Campaign_Tracker` metadata model

Table: `maddictdata.Metadata.Campaign_Tracker`. One row per
`(code_name, country)` pair.

| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER | `COALESCE(MAX(id),0)+1+{country_index}` at insert time — table-state-dependent, not a stable identifier across runs (see Compatibility Contract, §5) |
| `code_name` | INTEGER | Shared across all countries of one campaign |
| `campaign_name` | STRING | `{name}-{country}-{backend_report}` |
| `start_date` / `end_date` | DATE | |
| `country` | STRING | 3-letter code |
| `status` | STRING | `Pre-Validation → Validation → Active → Completion Period → Finished`, plus `Error`/`On Hold` |
| `type` | STRING | Drives `queries.ini` section selection — see `docs/code-audit.md` IH-005/IH-006 for how this can silently fail to match |
| `backend_report` | INTEGER | `0` means "no backend report expected" |
| `time_interval` | INTEGER | Gates *whether* a campaign is selected for a scheduled run; does **not** size the report window (`docs/code-audit.md` IH-019) |
| `last_update` | TIMESTAMP | Bumped by `update_last_update` at the end of every successful reporting run |
| `segments` | INTEGER (0/1) | Whether this campaign has audience segments |

---

## 3. Cloud vs. manual: shared run-service design (proposed)

The scheduled and manual paths currently duplicate authentication,
orchestration, and error handling, and **behave differently** for the same
campaign (`docs/code-audit.md` §3 of the original audit; IH-003's corrected
framing documents the recovery-path consequences). The proposed fix is not a
rewrite of the pipeline logic — that is explicitly out of scope for
`feature/safety-test-baseline` — but a target shape for a later branch:

```
runners/
  core.py        # ONE run_campaign(code_name, policy) function
  cloud.py        # thin: builds a "scheduled" RunPolicy, calls core.run_campaign
  manual.py       # thin: builds a "manual" RunPolicy, calls core.run_campaign
```

A `RunPolicy` is an explicit, testable object (not a boolean maze) that
controls:
- whether campaign **selection** happens (cloud: query for due campaigns;
  manual: a single `code_name` argument)
- whether the BER-upload return value gates continuation
- whether/when the `Finished` status write happens (see the proposed
  `Campaign_Runs` model below — the goal is to stop conflating "the tracker
  row says Finished" with "reporting actually completed successfully")
- how failures propagate (cloud: still return a response Cloud Functions
  accepts, but a *truthful* one, not always 200; manual: raise, so an
  operator sees it immediately)

Both `cloud.py` and `manual.py` become thin wrappers with no independent
business logic, closing the "two behaviors for one pipeline" gap.

### Proposed `Campaign_Runs` model

To fix the audit-trail gap in IH-003 (a manual recovery run is currently
indistinguishable from a scheduled one), add a new table,
`maddictdata.Metadata.Campaign_Runs`, written once per attempt:

| Field | Type | Notes |
|---|---|---|
| `run_id` | STRING (UUID) | Primary key for this attempt |
| `code_name` | INTEGER | Foreign key to `Campaign_Tracker` |
| `triggered_by` | STRING | `"scheduled"` or `"manual"` |
| `triggered_by_identity` | STRING | For manual runs, whoever/whatever invoked `custom_codename.py` (e.g. an operator identity or CI actor) |
| `started_at` / `finished_at` | TIMESTAMP | |
| `outcome` | STRING | `"success"`, `"failed"`, `"partial"` |
| `error_summary` | STRING, nullable | The exception, if any — currently swallowed entirely by IH-002 |
| `queries_run` | STRING (JSON array), nullable | Which query names actually executed, for partial-failure diagnosis |

This does **not** replace `Campaign_Tracker.status` — it sits alongside it as
an append-only audit log, so "is this campaign done" (status) and "what
happened on each attempt" (Campaign_Runs) are separate questions with
separate, honest answers. This table does not exist yet; it is a design
proposal for a future branch, not implemented here.

---

## 4. Goals and non-goals

**Goals:** preserve every trusted output while improving organization, test
coverage, safety (credential handling, UI write-surface), runtime
correctness, and operational recoverability.

**Non-goals for `feature/safety-test-baseline` specifically:** no pipeline
logic changes, no SQL/`queries.ini` changes, no schema changes, no Drive
re-layout, no dependency version bumps beyond what's needed for the test
venv, no changes to `.github/workflows/deploy.yml`, no new features.

**Non-goals for the modernization effort generally (until explicitly
revisited):** no UI redesign beyond closing the security gaps in
`docs/code-audit.md`; no change to the placelift statistical methodology
itself (only to its implementation's correctness); no migration off BigQuery
or Google Drive.

---

## 5. Target package structure

Constrained by one hard fact: CI deploys the Cloud Function from
`--source projects/automation` (`docs/code-audit.md` IH-034 context). Any
restructure must keep that directory deployable as a self-contained source
root, or the CI step must change in lockstep with the code move — never one
without the other.

```
infoharbor/                     # one installable package
  config/       settings.py      # ONE source of constants, replacing the
                                  # five divergent variables.py/input.py files
                queries/          # automation.ini, segments.ini (byte-identical
                                  # to today's content until explicitly revised)
  clients/      auth.py           # ONE get_secret / bq client / drive service
                bigquery.py       # run_query, run_query_get_res, run_query_save_table
                drive.py
  campaigns/    model.py repository.py   # CampaignConfig + tracker read/write
  tracker/      service.py
  segments/     extract.py split.py publish_drive.py publish_bq.py
  reporting/    orchestrator.py dates.py pipeline_types.py
  runners/      core.py cloud.py manual.py cli.py   # see §3
poi/                              # projects/poi/, evaluated for inclusion
                                   # once IH-036 is resolved
ui/                                # Flask, imports infoharbor only
tests/          unit/ fakes/ fixtures/ parity/
deploy/                            # packaging shim for the Cloud Function
```

---

## 6. Compatibility contract — "same results"

A refactor is output-equivalent iff, for a fixed campaign, fixed input data,
an injected fixed clock, and an injected seeded RNG, all of the following
match the pre-refactor baseline exactly:

- **Metadata rows** in `Campaign_Tracker` — all twelve fields, compared as a
  set of rows. `last_update` is compared only under an injected clock; `id`
  is compared only as a *relative* sequence (`ids[i] - ids[0] == i`), never
  as an absolute value, since it is a function of table state, not of input.
- **Resolved date windows** — the exact `(start_date_q, end_date_q,
  start_date_before, end_date_before)` tuple, and the exact `queries.ini`
  section name chosen from `type`.
- **Emitted SQL** — normalized (whitespace-collapsed) text of every query,
  plus its destination table and write disposition.
- **Distinct DIDs** — per segment, per country: row count and a SHA-256 hash
  of the sorted DID set.
- **Served/control relationships** — the control set must be disjoint from
  every served set (currently **violated** — `docs/code-audit.md` IH-007);
  the union of served + control must equal the pre-split eligible pool minus
  exclusions; control size must match exactly.
- **CSVs** — file names, header, row count, and SHA-256 of the sorted body
  (order-independent) *and* of the raw bytes (order-sensitive, and **not**
  portable across platforms — Windows emits `\r\n`, Linux `\n`; record this
  rather than assuming portability).
- **Drive** — folder path (`/YYYY/Qn/<campaign>/`), file titles, and file
  count per folder (this is what would catch IH-011, duplicate uploads).
- **BigQuery** — dataset/table names, schema (field name, type, order), row
  counts, and a content hash over sorted, canonically-formatted rows.

**Nondeterminism, and how it is neutralized without changing production
behavior** — see `tests/conftest.py` and `tests/unit/test_split_segments_control.py`
for the implementation: an unseeded `random.sample` call is made
reproducible by seeding Python's shared `random` module *from the test*
before calling the real, unmodified function; a frozen "now" is supplied by
monkeypatching the `datetime` name a module imports, never by adding a
`clock=` parameter to production code in this branch (that is a larger,
explicitly-scoped change for a later branch, once the pipeline itself is
being refactored).

**Deliberate exceptions to parity:** IH-003's status-ordering fix, IH-007's
served/control disjointness fix, IH-008's crash-guard fix, IH-009's
append-mode fix, IH-011's duplicate-upload fix, IH-017's date-argument-swap
fix, and IH-018's date-window fix are all *intended* to change output once
implemented — each is a bug, not a contract. Any PR implementing one of these
must state the before/after difference explicitly and get it approved,
exactly like every other parity exception.

**Known current gap:** true end-to-end parity for the *segments* stage is not
measurable until IH-001 is fixed, because `code_name` is read from
`projects/segments/input.py` rather than the campaign actually requested — a
parity run "for campaign 143" can silently operate on whatever campaign
`input.py` currently says. This branch's tests pin `input.py`'s content as an
explicit fixture rather than depending on its live, editable value; true
segments-stage parity is deferred to whichever branch fixes IH-001.

---

## 7. Testing strategy

- **Unit** — pure logic, no I/O: `get_run_dates`, `build_query` (both
  variants), the `type → section` mapping, `read_data_folder`/`get_control`
  exclusion and sampling logic, `CampaignConfig.validate`/`__post_init__`,
  `compare_columns` (the CSV-schema validator added to `upload_backend.py`
  on this branch).
- **Characterization** — pin *current* behavior, including known bugs, so a
  later refactor is provably behavior-preserving before any bug is fixed.
  Every such test carries an explicit `# BUG: IH-###` marker and is flipped
  (from "documents the bug" to "asserts the fix") in the same commit that
  fixes it. See `tests/unit/test_split_segments_control.py` and
  `tests/unit/test_pipeline_type_mapping.py` for the pattern.
- **Golden/parity** — hash-based comparison helpers in `tests/parity/manifest.py`
  (metadata-row hashing, DID-set hashing, CSV hashing both order-sensitive
  and order-independent, served/control disjointness reporting). Wiring these
  against real fixture data end-to-end is a follow-up task; this branch adds
  the helpers and tests them in isolation.
- **Fakes** — `tests/fakes/fake_bigquery.py` (records every query issued,
  its destination, and its write disposition; returns canned rows) and
  `tests/fakes/fake_drive.py` (in-memory file tree that deliberately
  *permits* duplicate titles, matching real Drive behavior, so IH-011 can
  eventually be tested without live Drive access).
- **Sandbox/integration (future, not in this branch)** — opt-in only,
  skipped by default, gated behind an explicit environment variable pointing
  at a non-production project/dataset. Never `maddictdata`.
- **Guardrail** — `tests/conftest.py`'s autouse `_block_real_cloud_clients`
  fixture monkeypatches the real Google client constructors to raise,
  so an accidental live call fails the test loudly instead of quietly
  reaching a real service.

---

## 8. Migration phases

- **Phase 0 — Baseline (this branch, in part).** Establish a working clone
  at the correct commit, an offline test foundation, and a complete,
  evidence-backed issue register. Determine (out of scope here, needs GCP
  read access) whether the deployed Cloud Function matches a commit in this
  repository's history (`docs/code-audit.md` IH-039).
- **Phase 1 — `feature/safety-test-baseline` (this branch).** Tests, fakes,
  fixtures, documentation. No behavior change to any production code path.
- **Phase 2 — Config unification.** One settings module; retire the five
  divergent `variables.py`/`input.py` files only after proving the merged
  values equal each existing copy field-by-field.
- **Phase 3 — Shared run-service core.** Implement the `runners/core.py` +
  `RunPolicy` design from §3; collapse the duplicated auth/orchestration
  between `main.py` and `custom_codename.py`.
- **Phase 4 — Correctness fixes.** One `docs/code-audit.md` finding per PR,
  Critical severity first, each with its regression test flipped from
  "documents the bug" to "asserts the fix," and an explicit parity-exception
  entry.
- **Phase 5 — Idempotency & recovery.** Delete-before-write/MERGE semantics
  where still missing (IH-031, IH-032), the `Campaign_Runs` audit model
  (§3), structured logging, truthful non-200 responses on failure.
- **Phase 6 — UI safety.** Authentication, CSRF, `debug=False`, and either
  removing or properly gating `/api/run-all-trackers`.
- **Phase 7 — Packaging & CI deploy gate.** `pyproject.toml`, a required
  test job before `deploy.yml` can run, pinned/complete dependencies,
  removal of `get-pip.py` and the stray `aaa` file (once IH-039 is
  resolved).

---

## 9. `feature/safety-test-baseline` — this branch's actual scope

See `docs/modernization-log.md` for the dated entry with the full file list,
test count, and validation results. In summary: an offline test foundation
(50 tests across unit/fakes/fixtures/parity), a non-deploying CI validation
workflow, the `.gitignore` fix that was blocking any test suite from ever
being committed, and this documentation set. No production pipeline logic
was changed.
