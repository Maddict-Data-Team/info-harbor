# Info-Harbor Code Audit Register

This is the living, per-finding issue register for the Info-Harbor modernization
effort. It exists so management and engineers can see, at a glance: what was
found, how severe it is, whether it has been fixed, and exactly what evidence
backs the claim. See `docs/modernization-log.md` for the chronological record of
work, and the root `README.md` "Modernization Status" section for a plain-language
summary.

**Audit baseline for this document:** branch `feature/safety-test-baseline`,
branched from `dev` at commit `810e30b5451e962bf7524bf8f22cb341322dda87` (a local
WIP commit made to preserve uncommitted work found on `dev`; the commit before
it, `296a157`, is the last commit that existed on `origin/dev` at audit time).
`dev` itself descends from `main` at `c0f2e3779c57de37aa48fa48b9edf92e4170b3cb`,
which was the originally-requested baseline. Every finding below was verified
by reading this branch's actual current file content, not carried over
unchecked from an earlier audit of `main` -- where a finding also existed
identically on `main`, that is noted.

**Severity:** Critical / High / Medium / Low
**Status:** Open / In Progress / Fixed / Accepted Risk / Needs Validation

A finding is only listed as a "Confirmed defect" if it was reproduced by reading
the exact current source (file + line) or by an automated test in `tests/`.
Anything not yet reproduced this way is listed under "Suspected issues requiring
validation" instead, however plausible it looks.

---

## Index

| ID | Title | Severity | Status |
|----|-------|----------|--------|
| [IH-001](#ih-001) | Wrong-campaign global override in segments query builder | Critical | Open |
| [IH-002](#ih-002) | Silent cloud pipeline failure -- bare `except` + unconditional HTTP 200 | Critical | Open |
| [IH-003](#ih-003) | Campaign marked `Finished` before reporting succeeds | High | Open |
| [IH-004](#ih-004) | Database-loaded campaigns lose segment definitions | Critical | Open |
| [IH-005](#ih-005) | `"Placelift NO BER"` bypasses the type normalizer and matches no section | Critical | **Fixed** |
| [IH-006](#ih-006) | `"Retail Intelligence Dashboard"` type mismatch | High | Open |
| [IH-007](#ih-007) | Served/control disjointness broken by a newline/whitespace mismatch | Critical | **Fixed** |
| [IH-008](#ih-008) | Control-pool subsampling crashes for segments under 100,000 raw DIDs | Critical | **Fixed** |
| [IH-009](#ih-009) | Raw segment CSVs opened in append mode; duplicate header/rows on rerun | High | **Fixed** |
| [IH-010](#ih-010) | `reset_folders()` never invoked by the default segments flow | High | Open |
| [IH-011](#ih-011) | Google Drive re-upload creates duplicate files on rerun | High | Open |
| [IH-012](#ih-012) | Unawaited tracker `INSERT` jobs; `id` assignment can race | Medium | In Progress |
| [IH-013](#ih-013) | `query_HG` SQL references an unbound alias | Medium | **Fixed** |
| [IH-014](#ih-014) | Broken `projects.campaign_tracker` import path | Medium | **Fixed** |
| [IH-015](#ih-015) | `projects/segments/main_new.py` fails at import | Medium | **Fixed** |
| [IH-016](#ih-016) | `get_metadata` reads the loop variable after the loop ends | Low | **Fixed** |
| [IH-017](#ih-017) | `[Common Queries]` recursion swaps date arguments (latent) | Medium | **Fixed** |
| [IH-018](#ih-018) | Bare-date `BETWEEN` window drops the final day / UTC-vs-local-day skew | High | Open |
| [IH-019](#ih-019) | `time_interval` accepted but never used in `get_run_dates` | Low | Open |
| [IH-020](#ih-020) | `SELECT DISTINCT *` dedupe can destroy legitimate duplicate rows | Medium | Open |
| [IH-021](#ih-021) | Backend-report file matching uses a Drive substring search | Medium | **Fixed** |
| [IH-022](#ih-022) | Stale external table reuse in `upload_backend.py` | Critical | **Fixed** |
| [IH-023](#ih-023) | `segments/main.py` `NameError` on undefined `bq_client` | Medium | **Fixed** |
| [IH-024](#ih-024) | `push_to_bq.py` external staging table `Conflict`-swallow | Medium | **Fixed** |
| [IH-025](#ih-025) | Flask UI has no authentication or CSRF protection on write routes | Critical | Open |
| [IH-026](#ih-026) | Flask app runs with `debug=True` on `host='0.0.0.0'` | Critical | **Fixed** |
| [IH-027](#ih-027) | Hardcoded Flask `secret_key` committed in source | High | Open |
| [IH-028](#ih-028) | `delete_from_drive.py` ships with `DELETE_MODE = True` by default | High | In Progress |
| [IH-029](#ih-029) | Inconsistent credential model (key files vs. Secret Manager) | Medium | Open |
| [IH-030](#ih-030) | Unparameterized SQL and Drive query-string interpolation throughout | High | Open |
| [IH-031](#ih-031) | `{codename}_visitors` uses `WRITE_APPEND` with an overlapping window | High | Open |
| [IH-032](#ih-032) | Combined `{code_name}_Segments` table appended without dedupe on rerun | Medium | Open |
| [IH-033](#ih-033) | O(lines) redundant Drive upload calls in the old `transfer_to_drive.py` | Low | **Fixed** |
| [IH-034](#ih-034) | CI deploys to production on every push to `main`, no tests, no gate | High | Open |
| [IH-035](#ih-035) | `pandas` imported by `data_validation.py` but undeclared in deployed requirements | Low | **Fixed** |
| [IH-036](#ih-036) | `projects/poi/` added with no tests, no CI wiring, no prior documentation | Medium | Needs Validation |
| [IH-037](#ih-037) | No test suite existed; `.gitignore`'s `test*` pattern actively blocked one | Critical | **Fixed** |
| [IH-038](#ih-038) | `projects/poi/` was undocumented prior to this branch | Low | **Fixed** |
| [IH-039](#ih-039) | `aaa` file may indicate repository/production drift | Medium | Needs Validation |
| [IH-040](#ih-040) | Unexplained `keys/test-google-sheet.json` credential file | Low | Needs Validation |
| [IH-041](#ih-041) | `/api/campaigns/add` reports success without persisting anything | Low | Needs Validation |
| [IH-042](#ih-042) | `.gitignore` fix revealed a previously-hidden, untracked, live-credential test script | Medium | Needs Validation |

---

## Confirmed defects

### IH-001
**Title:** Wrong-campaign global override in segments query builder
**Severity:** Critical
**Status:** Open
**Date discovered:** 2026-08-19

**Business impact:** Running the segments pipeline for one campaign can silently write another campaign's code name into the generated SQL, meaning audience data can be extracted, tagged, and published under the wrong campaign identifier without any error being raised.

**Technical explanation:** `build_query()` in `projects/segments/scripts/query_orchestrator.py` accepts a `codename` parameter, but the actual SQL substitution uses the module-level global `code_name` instead -- a name that is bound once, at import time, from `from input import *` (`projects/segments/input.py`). Every worker module in `projects/segments/scripts/` (`get_segments_raw.py`, `split_segments.py`, `push_to_bq.py`, `transfer_to_drive.py`, `create_be_table.py`) performs the same `from input import *` at its own import time, so each holds its own frozen copy of whatever `input.py` said at that moment. `main_new.py`'s attempt to fix this by injecting the requested campaign's variables into its *own* globals (`inject_campaign_variables(campaign_code_name, globals())`) cannot reach modules that were already imported with their own copies.

**Exact file and line evidence:**
- `projects/segments/scripts/query_orchestrator.py:135-136` -- `build_query(query, country, codename=0, radius=0, segment="", filters="")`
- `projects/segments/scripts/query_orchestrator.py:162` -- `query = query.replace("{code_name}", code_name)` (uses the global, not the `codename` parameter above)
- `projects/segments/scripts/query_orchestrator.py:17` -- `from input import *` (binds `code_name` at import time)
- `projects/segments/input.py:1` -- `code_name = "183"` (current value on this branch; was `"167"` on the `main` baseline)

**How to reproduce / verify safely:**
```
python -m pytest tests/unit/test_segments_wrong_campaign_global.py -v
```
This monkeypatches the module's `code_name` global to a sentinel value distinct from an explicitly-passed `codename="143"` argument, calls the real `build_query()`, and asserts the sentinel (not `"143"`) appears in the output. No network, no credentials.

**Recommended correction:** Have `build_query` use its `codename` parameter exclusively; remove the `{code_name}` placeholder's dependence on the module global, or explicitly re-derive it from the parameter at the top of the function. This is a pipeline-logic change and is **out of scope** for `feature/safety-test-baseline` -- it belongs in a dedicated correctness-fix branch, informed by this finding's regression test.

**Tests required:** `tests/unit/test_segments_wrong_campaign_global.py` (added, passing, characterizes the bug). A second test proving the *fix* once one lands (assert the parameter wins, not the global).

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

### IH-002
**Title:** Silent cloud pipeline failure -- bare `except` + unconditional HTTP 200
**Severity:** Critical
**Status:** Open
**Date discovered:** 2026-08-19 (identical on `main` at `c0f2e37`; file unchanged on this branch)

**Business impact:** When the scheduled reporting run fails for any reason -- misconfigured campaign type, a BigQuery error, a bad date -- the Cloud Function still reports success. Nobody is alerted; the failure is only visible if someone manually reads Cloud Function logs.

**Technical explanation:** `run_by_codename()` wraps the entire reporting pipeline in a bare `except:` that prints a traceback and returns the string `"error"`. The caller discards that return value. The top-level Cloud Function entry point then always returns HTTP 200 regardless of what happened inside.

**Exact file and line evidence:**
- `projects/automation/query_orchestrator.py:427-429`:
  ```
      except:
          traceback.print_exc()
          return "error"
  ```
- `projects/automation/main.py:91-92` -- the loop that calls `run_by_codename` and never inspects its return value
- `projects/automation/main.py:133-136`:
  ```
  def main(request=None):
      query_bigquery_and_process()
      return ("Function executed successfully", 200)
  ```
- Secondary swallow: `projects/automation/main.py:68-70` (`except Exception as e: print(...); continue` around the BER upload step)

**How to reproduce / verify safely:** Static reading confirms the control flow directly (no runtime call needed to see that every code path through `main()` reaches the same `return (..., 200)`). `tests/unit/test_pipeline_type_mapping.py` proves one concrete trigger for the `except:` (a `NoSectionError` from IH-005/IH-006) without touching BigQuery.

**Recommended correction:** Re-raise or propagate a non-200 response on failure; replace the bare `except:` with typed exception handling that distinguishes "skip this campaign, continue with others" from "the whole run failed."

**Tests required:** An integration-style test with `tests/fakes/fake_bigquery.py` that forces `run_by_codename` to raise, then asserts the Cloud Function's HTTP response reflects the failure (requires the pipeline-logic fix first; the current code has no failure-reporting path to test).

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

### IH-003
**Title:** Campaign marked `Finished` before reporting succeeds
**Severity:** High
**Status:** Open
**Date discovered:** 2026-08-19 (identical on `main`; file unchanged on this branch)

**Business impact -- corrected framing:** A campaign whose final reporting run fails is still marked `Finished` in the tracker. **This does not make the campaign unrecoverable** -- `custom_codename.py` selects by `code_name` with no status filter, so an operator can manually rerun it. The real risks are: (1) **automatic retry is permanently lost**, since the scheduled selection query excludes `Finished` rows; (2) **manual recovery is unaudited** -- nothing distinguishes a manual rerun from a normal scheduled one in the tracker; (3) a manual rerun is **not idempotent**, so it can duplicate appended data (IH-031) or reuse a stale intermediate table if run between two runs' half-completed state.

**Technical explanation:** `start_the_process()` issues an `UPDATE ... SET status = 'Finished'` as soon as a row's status is `Completion Period`, *before* `run_by_codename()` (the actual reporting work) is called for that code name.

**Exact file and line evidence:**
- `projects/automation/main.py:76-84`:
  ```
      if status == stage_3:
          print(f"Updating for {code_name} because it's status is {status}")
          update_query = f"""
              UPDATE `maddictdata.Metadata.{tbl_cmpgn_tracker}`
              SET status = 'Finished'
              WHERE id = {id};
          """
          run_query(update_query, bq_client)
  ```
- `projects/automation/main.py:91-92` -- `run_by_codename` is only called after the loop above, for the set of `unique_code_names` collected during it
- Automatic-retry loss: `projects/automation/variables.py:119` (`WHERE status NOT IN ('Finished', 'On Hold')`) and `:129-133` (`q_select_active_interval`, which only selects `Active`+interval-due or `Completion Period` rows)
- Manual recovery remains possible: `projects/automation/custom_codename.py:37-40` calls `get_campaign_tracker_data`, which runs `[Setup] query_metadata` (`projects/automation/queries.ini:6-8`) -- `WHERE code_name = {codename}`, with **no status filter**
- Recovery is unaudited: `run_by_codename` ends with `update_last_update` (`query_orchestrator.py:426`), which bumps `last_update` identically whether the run was scheduled or manual; nothing records which
- Recovery is not idempotent: a rerun re-appends to `{codename}_visitors` (IH-031) and, prior to this branch's fix, could reuse a stale `{backend_report}_new` table (IH-022, now Fixed)

**How to reproduce / verify safely:** Static reading of the ordering above. Also hardcodes the literal `'Finished'` instead of the `stage_4` constant (`projects/automation/variables.py:46`), a minor internal-consistency issue noted alongside this finding.

**Recommended correction:** Move the status write to occur only after `run_by_codename` succeeds for that code name; add a distinct status or audit column (see `docs/modernization-spec.md`'s proposed `Campaign_Runs` model) that records whether a run was scheduled or manual, and its outcome.

**Tests required:** Once the pipeline is refactored to separate "mark complete" from "ran successfully," a test asserting the status write only happens after a successful `FakeBigQueryClient`-backed run.

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

### IH-004
**Title:** Database-loaded campaigns lose segment definitions
**Severity:** Critical
**Status:** Open
**Date discovered:** 2026-08-19 (identical on `main`; file unchanged on this branch)

**Business impact:** When campaign configuration is loaded from BigQuery (the primary path), every campaign silently loses its list of audience segments, custom segment filters, and exclusion list -- even for campaigns whose real segment definitions exist in the hardcoded fallback files.

**Technical explanation:** `create_campaign_config_from_db()` builds a `CampaignConfig` with `segments=[]`, `custom_segments={}`, `excluded_segments=[]` hardcoded, because those fields are not read from the database. Worse, `_load_campaigns()` replaces the entire hardcoded registry with the database result set whenever the database is reachable, rather than merging the two, so a campaign that previously had real segment data available via the hardcoded fallback loses it as soon as the database path succeeds.

**Exact file and line evidence:**
- `shared/config/campaigns/database_loader.py:94-113`, specifically `:108-110`:
  ```
          # Default values for fields not in database
          segments=[],
          custom_segments={},
          excluded_segments=[],
  ```
- `shared/config/campaigns/__init__.py:27-35`:
  ```
          db_campaigns = get_database_campaigns()
          if db_campaigns:
              print(f"[OK] Loaded {len(db_campaigns)} campaigns from database")
              _campaigns_cache = db_campaigns
              return _campaigns_cache
  ```
  (replaces, does not merge with, `HARDCODED_CAMPAIGNS`)

**How to reproduce / verify safely:** Static reading; a live reproduction would require a real BigQuery connection to `Campaign_Tracker`, which is out of scope for this offline audit and this branch.

**Recommended correction:** Extend the `Campaign_Tracker` schema (or a related table) to store segment definitions, or merge database-sourced fields with the hardcoded fallback per campaign rather than replacing the whole registry.

**Tests required:** A unit test asserting `create_campaign_config_from_db` preserves segment data once the schema/merge logic changes; until then, a characterization test asserting current (broken) behavior would be useful in a follow-up branch.

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

### IH-005
**Title:** `"Placelift NO BER"` bypasses the type normalizer and matches no `queries.ini` section
**Severity:** Critical
**Status:** Fixed
**Date discovered:** 2026-08-19 (identical on `main`; file unchanged on this branch)

**Business impact:** A campaign whose `type` is stored as exactly `"Placelift NO BER"` (as opposed to being derived by the normalizer) produces **zero reporting output on every scheduled run**, and every run reports success (IH-002). This was traced with the exact reproduction case supplied by the project owner: `code_name=113`, `type="Placelift NO BER"`, `backend_report=0`, `segments=1`.

**Technical explanation:** `get_metadata()`'s normalizer block only rewrites five exact literal strings (`"Placelift Report"`, `"Placelift Dashboard"`, `"Placelift"`, `"Standard Placelift"`, `"Comparative Analysis"`). `"Placelift NO BER"` is none of them, so it passes through unchanged. The real `queries.ini` section is `[Placelift No BER]` (mixed case: `No`, not `NO`). Python's `configparser` lowercases *option* names but keeps **section names case-sensitive**, so `config.get("Placelift NO BER", "queries")` raises `configparser.NoSectionError`, which is then swallowed by IH-002.

Note the irony this traces out: a campaign with `segments=1, backend_report=0` and a *plain* `type="Placelift"` (or `"Standard Placelift"`, etc.) **would** resolve, via the normalizer's `elif backend_report == 0` branch, to exactly `"Placelift No BER"` -- the correct section. Writing the target section name directly into the metadata is precisely what breaks it.

**Exact file and line evidence:**
- `projects/automation/query_orchestrator.py:223-229` (the normalizer's exact literal list)
- `projects/automation/query_orchestrator.py:290` -- `queries = config.get(pipeline_type, "queries").split(",")`
- `projects/automation/queries.ini:429` -- `[Placelift No BER]` (confirmed via case-sensitive grep: no section anywhere in the file uses uppercase `NO`)

**How to reproduce / verify safely:**
```
python -m pytest tests/unit/test_pipeline_type_mapping.py -v -k PlacementNoBer
```
This builds the exact `code_name=113` row via `tests/fixtures/campaign_metadata.py::placelift_no_ber_113`, feeds it through the real `get_metadata()` against a `FakeBigQueryClient`, and confirms (a) the type is *not* rewritten by the normalizer (correct, unrelated to this fix -- "Placelift NO BER" is not one of the 5 base literals `get_metadata` normalizes) and (b) `resolve_section_case_insensitive()` now resolves it to the real `"Placelift No BER"` section, which `config.get()` accepts without raising. No network, no credentials.

**Fix applied:** Added `resolve_section_case_insensitive(config, section_name)` to `projects/automation/query_orchestrator.py` (new function, just above `run_pipeline_queries`): returns `section_name` unchanged if `config.has_section(section_name)` already holds; otherwise scans `config.sections()` for a case-insensitive match and returns that instead; falls through to the original string unchanged if neither matches, so a genuinely-absent section still raises `NoSectionError` rather than being masked. `run_pipeline_queries` now calls it once, immediately after the "Starting queries" print, before its first `config.get(pipeline_type, ...)` -- the resolved value is then reused for every subsequent lookup in that call (including the per-query `config.get(pipeline_type, query_name)`). `get_metadata()`'s normalizer itself was **not** touched -- the fix is at the section-resolution boundary, not the type-string boundary, per the "canonicalize at write time" alternative in the original recommended correction being out of scope (it lives in a different project, campaign-tracker, and is a production-write-path change).

**Recommended correction:** ~~Normalize `type` comparisons case-insensitively (or canonicalize at write time in the campaign-tracker)~~ Done, via case-insensitive section resolution at the `queries.ini` lookup boundary. The second half -- ~~add a startup-time validation step that checks every distinct `type` value present in `Campaign_Tracker` against the section list, failing loudly instead of silently~~ -- is **not implemented**; it requires a live `Campaign_Tracker` read to enumerate distinct values and is a larger, separate feature, flagged as a good follow-up task.

**Tests required:** `tests/unit/test_pipeline_type_mapping.py` -- `TestConfirmedPlacementNoBerMismatch::test_resolve_section_case_insensitive_finds_the_correct_section` (new, replaces the old BUG-marked end-to-end test; proves the resolver finds `"Placelift No BER"`), `test_raw_lookup_still_raises_without_resolution` (kept, proves the fix is scoped to `run_pipeline_queries`'s call site, not a global configparser monkeypatch), and `TestConfirmedUnknownTypeMismatch::test_resolver_does_not_mask_a_genuinely_absent_section` (new, guards against over-reach for a type with no match at all).

**Branch/PR/commit that fixes it:** `feature/safety-test-baseline` (this branch).
**Date resolved:** 2026-08-20

---

### IH-006
**Title:** `"Retail Intelligence Dashboard"` type mismatch
**Severity:** High
**Status:** Open
**Date discovered:** 2026-08-19 (identical on `main`; file unchanged on this branch)

**Business impact:** Retail campaigns configured with the hardcoded fallback type silently produce no reports; same failure class as IH-005, same silent swallow via IH-002.

**Technical explanation:** `campaign_144_retail.py` sets `type="Retail Intelligence Dashboard"`. The only matching `queries.ini` section is `[Retail Intelligence]` (no `"Dashboard"` suffix), and this string is not one of the five literals the normalizer rewrites.

**Exact file and line evidence:**
- `shared/config/campaigns/campaign_144_retail.py:12` -- `type="Retail Intelligence Dashboard"`
- `projects/automation/queries.ini:236` -- `[Retail Intelligence]`
- `projects/automation/query_orchestrator.py:223-229` (normalizer does not cover this string)

**How to reproduce / verify safely:**
```
python -m pytest tests/unit/test_pipeline_type_mapping.py -v -k RetailIntelligence
```

**Recommended correction:** Either rename the section to match the campaign config's `type` value, or vice versa; add the startup-time validation recommended under IH-005 to catch the whole class of mismatch at once.

**Tests required:** `tests/unit/test_pipeline_type_mapping.py` (added, passing).

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

### IH-007
**Title:** Served/control disjointness broken by a newline/whitespace mismatch
**Severity:** Critical
**Status:** Fixed
**Date discovered:** 2026-08-19 -- **NEW on this branch**; this file did not have this bug at the `main` baseline (`c0f2e37`). The whole `read_data_folder`/`Write_output_to_files` pair in `projects/segments/scripts/split_segments.py` was rewritten as part of the uncommitted work found on `dev` (now committed as `810e30b`, see `docs/modernization-log.md` entry 2026-08-19).

**Business impact:** The control group is supposed to be excluded from the served (exposed) audience -- that separation is the entire statistical basis for a placelift measurement. On this branch, that exclusion silently does not happen: every control-group device ID is *also* written into the served output, contaminating every placelift report this pipeline produces.

**Technical explanation:** `Write_output_to_files()` rewrites the served CSV by re-reading each raw file and checking `if did not in control:` before writing. `did` here is a **raw line from the file object**, which includes the trailing `"\n"`; `control` is a `set` of **already-stripped** DID strings (built earlier by `get_control()`, which strips lines before sampling). A string with a trailing newline is never equal to its stripped counterpart, so `did not in control` is `True` for every row, unconditionally -- the exclusion check can never fire.

**Exact file and line evidence:**
- `projects/segments/scripts/split_segments.py:119-132`:
  ```
          with open("projects/segments/data/raw/" + file) as inpf:
              inpf.readline()
              with open(
              "projects/segments/data/served/" + names[i] + "_served.csv", "w"
              ) as outf:
                  outf.write("DID\n")
                  for did in inpf:
                      if did not in control:
                          outf.write(did.strip() + "\n")
  ```
- `control` is built as stripped strings by `get_control()`: `projects/segments/scripts/split_segments.py:82-84`:
  ```
      controlled_segment = random.sample(sorted(for_controlled), controlled_size)
      controlled_segment = set(controlled_segment)
  ```
  where `for_controlled` was built from `line.strip()` values at `:65`.

**How to reproduce / verify safely:**
```
python -m pytest tests/unit/test_split_segments_control.py -v -k TestServedControlDisjointness
```
This calls the real `Write_output_to_files()` against a temp fixture directory (via the `isolated_segments_workspace` fixture) and now asserts that DIDs placed in the control set are absent from the resulting served CSV, and that served equals the raw set minus control. No network, no credentials.

**Fix applied:** `projects/segments/scripts/split_segments.py:131` now compares `did.strip()` against `control` instead of the raw line (`if did.strip() not in control:`). No other line in `Write_output_to_files()` changed.

**Recommended correction:** ~~Compare `did.strip()` (or the already-consistent stripped values) against `control`, not the raw line.~~ Done.

**Tests required:** `tests/unit/test_split_segments_control.py::TestServedControlDisjointness` (flipped from `TestServedControlOverlapBug`; now asserts disjointness instead of documenting the overlap).

**Branch/PR/commit that fixes it:** `feature/safety-test-baseline` (this branch).
**Date resolved:** 2026-08-20

---

### IH-008
**Title:** Control-pool subsampling crashes for segments under 100,000 raw DIDs
**Severity:** Critical
**Status:** Fixed
**Date discovered:** 2026-08-19 -- **NEW on this branch** (same rewrite as IH-007).

**Business impact:** Any segment with fewer than 100,000 raw device IDs -- a realistic size for most custom or niche segments -- crashes the entire `split_files()` run with an unhandled exception, halting segment processing for the whole campaign, not just that one segment.

**Technical explanation:** `read_data_folder()` now calls `random.sample([line.strip() for line in inpf], k=100000)` unconditionally for every segment file, with no check that the file actually has 100,000 lines. `random.sample` raises `ValueError: Sample larger than population or is negative` whenever the population is smaller than `k`.

**Exact file and line evidence:**
- `projects/segments/scripts/split_segments.py:64-65`:
  ```
              # strip any spaces or new lines and save the DID in a set
              temp_set = set(random.sample([line.strip() for line in inpf],k=100000))
  ```

**How to reproduce / verify safely:**
```
python -m pytest tests/unit/test_split_segments_control.py -v -k TestControlPoolSubsamplingBelowThreshold
```
Writes a 50-line fixture raw CSV, asserts `read_data_folder()` returns every DID, and verifies `get_control()` selects 25 DIDs (the approved 50% proportional rule) without raising. It also verifies that an empty eligible pool returns an empty control set. No network, no credentials.

**Fix applied:** `projects/segments/scripts/split_segments.py:64-66` materializes the candidate population and bounds the initial sample. Following review, `get_control()` now also handles the downstream undersized-pool path: it preserves the configured 50,000-of-100,000 ratio by selecting 50% of an eligible pool below 100,000 DIDs, capped at 50,000. Empty pools return an empty set; non-empty pools select at least one DID.

**Recommended correction:** ~~Guard both sampling stages and define the undersized-pool behavior.~~ Done. The approved interim rule is proportional reduction to 50% for pools below 100,000; this decision is recorded in the root README for later review with the placelift methodology owner. The separate question of whether the 100,000-per-file candidate cap is statistically correct remains unresolved.

**Tests required:** `tests/unit/test_split_segments_control.py::TestControlPoolSubsamplingBelowThreshold` now covers candidate retention, proportional control selection, and the empty-pool boundary.

**Branch/PR/commit that fixes it:** `feature/safety-test-baseline` (this branch).
**Date resolved:** 2026-08-20

---

### IH-009
**Title:** Raw segment CSVs opened in append mode; duplicate header/rows on rerun
**Severity:** High
**Status:** Fixed
**Date discovered:** 2026-08-19 (present at main; file changed on this branch but the append-mode bug survived the rewrite)

**Business impact:** Rerunning segment extraction for the same campaign on the same day appends a second `DID` header row into the middle of the raw CSV and duplicates every device ID already fetched, inflating segment counts and corrupting downstream files.

**Technical explanation:** `get_raw_segments()` opens the per-segment raw CSV with mode `'a'` (append) and unconditionally writes a `"DID\n"` header on every call, keyed only by a same-day timestamp in the filename (`%Y%m%d`). Nothing clears this file between runs unless `reset_folders()` is called first (see IH-010).

**Exact file and line evidence:**
- `projects/segments/scripts/get_segments_raw.py:45` -- `now = datetime.datetime.now().strftime("%Y%m%d")`
- `projects/segments/scripts/get_segments_raw.py:50-51`: the file is opened with `'a'` and `outf.write("DID\n")` runs unconditionally on every call.

**How to reproduce / verify safely:**
```
python -m pytest tests/unit/test_get_segments_raw_rerun.py -v
```
Calls the real `get_raw_segments()` twice in a row against a monkeypatched `query_orchestrator.run_query_behavior` (no BigQuery), and asserts the resulting file has exactly one `DID` header and no duplicated rows after the second call -- the exact rerun scenario this finding describes.

**Fix applied:** `projects/segments/scripts/get_segments_raw.py:50`: `open(..., 'a')` -> `open(..., 'w')` (truncate-then-write, the recommended correction's first option). The unconditional header write was already correct for a fresh file; changing only the mode makes every open a fresh file, matching that assumption instead of contradicting it. Did not implement the "fail fast if the file already exists" alternative -- that would introduce new error behavior where none exists today, a larger behavior change for the same underlying goal.

**Recommended correction:** ~~Open with mode `'w'`... or truncate-then-write~~ Done.

**Tests required:** `tests/unit/test_get_segments_raw_rerun.py` (new, 1 test) -- the "mocking the BigQuery row iterator" this was deferred pending turned out to be a straightforward `monkeypatch.setattr` on `query_orchestrator.run_query_behavior`, not requiring a follow-up branch after all.

**Branch/PR/commit that fixes it:** `feature/safety-test-baseline` (this branch).
**Date resolved:** 2026-08-20

---

### IH-010
**Title:** `reset_folders()` never invoked by the default segments flow
**Severity:** High
**Status:** Open
**Date discovered:** 2026-08-19 -- worse on this branch than at main: main had the reset call commented out too, but this branch's `projects/segments/main.py` was substantially rewritten and still leaves it commented out.

**Business impact:** Directly enables IH-009 (and stale-file accumulation generally): without a folder reset between runs, `data/raw`, `data/served`, and `data/controlled` accumulate files from every prior run of every prior campaign that used this machine/environment.

**Technical explanation:** `projects/segments/main.py`'s `main()` calls `authenticate_get_clients()`, then `move_without_splitting()` (not even `split_files()`), `transfer_files_to_drive()`, `run_push_to_bq()`, `create_BER_Table()` -- `reset_folders()` and `get_raw_segments()` are both commented out.

**Exact file and line evidence:**
- `projects/segments/main.py:46-52` -- the calls to `reset_folders()` and `get_raw_segments(...)` are both commented out immediately after `bq_client, drive_service = authenticate_get_clients()`.

**How to reproduce / verify safely:** Static reading; the comments are unambiguous.

**Recommended correction:** Either uncomment the reset/fetch steps (if this file is meant to be runnable end-to-end) or, if it is intentionally a partial/manual-step script, document that clearly at the top of the file so an operator does not assume a clean run.

**Tests required:** None specific; covered indirectly by any future integration test asserting a full run starts from an empty `data/` tree.

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

### IH-011
**Title:** Google Drive re-upload creates duplicate files on rerun
**Severity:** High
**Status:** Open
**Date discovered:** 2026-08-19 (present at main; `transfer_to_drive.py` was substantially rewritten on this branch -- see IH-033 for what that rewrite fixed -- but this specific defect was not addressed)

**Business impact:** Rerunning the segments pipeline (accidentally, or as part of a manual recovery per IH-003) creates additional same-named CSV files in the campaign's Drive folder rather than replacing the existing one. Google Drive permits duplicate titles in one folder, so nothing prevents this, and downstream consumers of that folder (including `push_to_bq.py`'s external-table step) may pick up whichever file id happens to be returned.

**Technical explanation:** `transfer()` unconditionally calls `service.files().create(...)` for every `.csv` file found under the data directory; there is no check for an existing file with the same name in the destination folder before uploading, and no delete-then-upload step.

**Exact file and line evidence:**
- `projects/segments/scripts/transfer_to_drive.py:133-186` (the `try:` block that always calls `service.files().create(body=metadata, ...)`, both the resumable and non-resumable branches)
- `find_or_create_folder()` (`:54-78`) reuses the existing campaign folder by design (correct for folders), but nothing analogous exists for files

**How to reproduce / verify safely:** Static reading; `tests/fakes/fake_drive.py` is deliberately built to permit duplicate titles (matching real Drive behavior) so a future regression test can assert this without hitting real Drive -- not yet wired in, since exercising it meaningfully requires making `transfer_to_drive.py` accept an injectable Drive service, which is pipeline-logic work out of scope for this branch.

**Recommended correction:** Before uploading, search the destination folder for a file with the same name; delete it (or version it) before creating the new one.

**Tests required:** A test using `tests/fakes/fake_drive.py::FakeDriveService`, once `transfer_to_drive.py` is refactored to accept an injectable Drive service.

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

### IH-012
**Title:** Unawaited tracker `INSERT` jobs; `id` assignment can race
**Severity:** Medium
**Status:** In Progress
**Date discovered:** 2026-08-19 (identical on main; `projects/campaign-tracker/main.py` unchanged on this branch)

**Business impact:** Campaign metadata rows can silently fail to be written (the failure is never surfaced), and under concurrent execution, two countries' rows can compute the same "next id" and either collide or leave a gap.

**Technical explanation:** `metadata_placelift()` calls `client.query(query)` for each country's `INSERT` without calling `.result()`, so the BigQuery job is fired and forgotten; any job-level error is invisible to the caller. Each country's `INSERT` independently recomputes `COALESCE(MAX(id), 0) + 1 + {index}` from current table state, so if the jobs are not strictly ordered, two countries can observe the same `MAX(id)`.

**Exact file and line evidence:**
- `projects/campaign-tracker/main.py:70-71` -- `client.query(query)` with no `.result()` call
- `projects/campaign-tracker/main.py:55` -- `COALESCE(MAX(id), 0) + 1 + {index}`

**How to reproduce / verify safely:** Static reading; reproducing the race requires a real BigQuery table under concurrent load, out of scope offline.

**Fix applied (partial):** `projects/campaign-tracker/main.py:70-73`: `client.query(query)` -> `client.query(query).result()`. A failed `INSERT` now raises instead of being silently fired-and-forgotten -- `metadata_placelift()` has no surrounding `try/except`, so the exception propagates to the caller. **Not fixed:** the `id`-assignment race itself (`COALESCE(MAX(id), 0) + 1 + {index}`, recomputed independently per country) -- moving to a single multi-row `INSERT` or a surrogate key generator is a genuine design choice between two different mechanisms, not a single-answer bug fix, and is added to the decision queue.

**Recommended correction:** ~~Call `.result()` on the query job~~ Done. ~~Move to a single multi-row `INSERT ... VALUES`... or use a proper surrogate key generator~~ not implemented -- design decision, see decision queue.

**Tests required:** None offline-testable without a live BigQuery table (unchanged from the original assessment) -- `create_client()` builds a real client with no injection point; making it testable would need the same kind of refactor IH-011 needs for `transfer_to_drive.py`, out of scope for this fix.

**Branch/PR/commit that fixes it:** `feature/safety-test-baseline` (this branch) -- partial (visibility fix only).
**Date resolved:** N/A -- race condition remains open

---

### IH-013
**Title:** `query_HG` SQL references an unbound alias
**Severity:** Medium
**Status:** Fixed
**Date discovered:** 2026-08-19 (identical on main; `projects/segments/queries.ini` unchanged on this branch)

**Business impact:** Any campaign that uses the `HG` ("Near By Residents") segment type will fail with a SQL error the moment that segment is queried.

**Technical explanation:** The query aliases the home-graph table as `HG` but its join predicate references `ls.Longitude` / `ls.latitude` -- an alias (`ls`) that is never bound anywhere in the query.

**Exact file and line evidence:**
- `projects/segments/queries.ini:18-23` -- `query_HG` aliases the source table `as HG` at line 19, then references `ls.Longitude`/`ls.latitude` at line 23.

**How to reproduce / verify safely:**
```
python -m pytest tests/unit/test_segments_queries_ini.py -v
```
Static text check confirming `query_HG` now references only `HG.*`/`poi.*` and no longer contains `ls.`. Confirming the query previously raised a live BigQuery error is not re-verified here -- that requires a live query, out of scope offline; the unbound-alias evidence itself was conclusive from static reading.

**Fix applied:** `projects/segments/queries.ini`'s `query_HG` (line 23): `ls.Longitude,ls.latitude` -> `HG.Longitude,HG.latitude`, matching the alias the query itself declares (`` `{project}.{hwg_dataset}.{hg_table}` as HG ``, line 19). `ls` was almost certainly left over from `query_POI` immediately above it in the same file, which does declare an `ls` alias for a different table. **Scope note:** this edits `projects/segments/queries.ini`, which `docs/modernization-spec.md` §4 lists under this branch's non-goals ("no SQL/queries.ini changes"). Made anyway under the same explicit user authorization already covering the pipeline-logic-change deviation (see the 2026-08-20 IH-007/IH-008 log entry) -- the fix has exactly one correct answer (bind to the table the query actually joins), and it turns a query that currently hard-fails on every use into a working one, with no silent-output-change risk.

**Recommended correction:** ~~Change `ls.Longitude`/`ls.latitude` to `HG.Longitude`/`HG.latitude`~~ Done. The suggested longer-term static linter (checking every query template's aliases generally) was not added -- out of scope for this single-finding fix; a narrower, finding-specific regression test was added instead.

**Tests required:** `tests/unit/test_segments_queries_ini.py` (new, 1 test) -- narrower than the general linter idea above, scoped to this specific query.

**Branch/PR/commit that fixes it:** `feature/safety-test-baseline` (this branch).
**Date resolved:** 2026-08-20

---

### IH-014
**Title:** Broken `projects.campaign_tracker` import path
**Severity:** Medium
**Status:** Fixed
**Date discovered:** 2026-08-19 (identical on main; both call sites unchanged on this branch, and a third call site was added -- see IH-025)

**Business impact:** Every UI action and CLI path that is supposed to run the campaign tracker fails immediately with `ModuleNotFoundError`, silently caught and shown only as a flash message or swallowed error in the UI.

**Technical explanation:** The real directory is `projects/campaign-tracker` (hyphen), which is not a syntactically valid Python package/module name. Code that does `from projects.campaign_tracker.main_new import main` (underscore) can never resolve.

**Exact file and line evidence:**
- `ui/app.py:130` -- `from projects.campaign_tracker.main_new import main as tracker_main` (inside `run_campaign_action`)
- `ui/app.py:161` -- second occurrence inside `api_run_campaign_action`
- `ui/app.py:198` -- third occurrence inside `api_run_all_trackers` (new on this branch, see IH-025)
- `campaign_manager.py:111` -- same broken import, unchanged file (identical to main baseline)
- No `__init__.py` exists anywhere under `projects/` on this branch (confirmed via directory listing), so this is a real, unconditional `ModuleNotFoundError`, not merely a style issue.

**How to reproduce / verify safely:**
```
python -m pytest tests/unit/test_campaign_tracker_import_path.py -v
```
Confirms `from shared.utils.compatibility import get_campaign_tracker_main_new; get_campaign_tracker_main_new()` returns a callable `main`, and separately confirms the original dotted import still raises `ModuleNotFoundError` (so a future reader isn't tempted to "simplify" the fix back to a normal import).

**Fix applied:** Added `load_module_from_path(module_name, file_path)` (general helper) and `get_campaign_tracker_main_new()` (specific to this finding) to `shared/utils/compatibility.py`, using `importlib.util.spec_from_file_location` -- the same pattern already used by `projects/segments/scripts/*.py` to load `variables.py`. Replaced all 4 broken call sites (`ui/app.py:129-130, 165-166, 198-199`; `campaign_manager.py:111-112`) with `from shared.utils.compatibility import get_campaign_tracker_main_new` + `tracker_main = get_campaign_tracker_main_new()`. Did not rename the `projects/campaign-tracker/` directory (the recommended correction's other option) -- renaming risks breaking other external references (docs, Drive paths, scripts) to the hyphenated path, while the importlib fix is scoped entirely to the 4 broken call sites.

**Recommended correction:** ~~change every import site to the correct path via `importlib` machinery matching the hyphen~~ Done.

**Tests required:** `tests/unit/test_campaign_tracker_import_path.py` (new, 2 tests).

**Branch/PR/commit that fixes it:** `feature/safety-test-baseline` (this branch).
**Date resolved:** 2026-08-20

---

### IH-015
**Title:** `projects/segments/main_new.py` fails at import
**Severity:** Medium
**Status:** Fixed
**Date discovered:** 2026-08-19 (identical on main; file unchanged on this branch)

**Business impact:** The "new," shared/-config-based segments entry point cannot run at all; any caller (`ui/app.py`, `campaign_manager.py`) that imports it fails before doing any work.

**Technical explanation:** `main_new.py` imports the worker scripts as `from projects.segments.scripts.get_segments_raw import get_raw_segments` etc., but those scripts themselves do flat imports (`import query_orchestrator`, `from variables import *`) that require `projects/segments/scripts` to be on `sys.path`. Unlike `projects/segments/main.py` (which does `sys.path.append(scripts_dir)` before importing them), `main_new.py` never adds that directory.

**Exact file and line evidence:**
- `projects/segments/main_new.py:22-28` (the `from projects.segments.scripts.* import *` block, with no preceding `sys.path` manipulation for `scripts/`)
- Contrast: `projects/segments/main.py:11-14` does add `scripts_dir` to `sys.path` before its own (flat-style) imports

**How to reproduce / verify safely:**
```
python -m pytest tests/unit/test_segments_main_new_import.py -v
```
Before the fix, empirically confirmed with `python -c "import projects.segments.main_new"` -> `ModuleNotFoundError: No module named 'query_orchestrator'` (the venv used to verify all fixes on this branch, not an ad hoc environment).

**Fix applied:** `projects/segments/main_new.py` now does `scripts_dir = project_root / "projects" / "segments" / "scripts"; sys.path.append(str(scripts_dir))` immediately before the `from projects.segments.scripts.* import *` block -- mirroring `projects/segments/main.py:11-15`'s existing pattern exactly. Did not convert the worker scripts to package-relative imports (the recommended correction's other option) -- that would touch every file under `projects/segments/scripts/`, a much larger change for the same outcome.

**Recommended correction:** ~~Add the missing `sys.path.append(...)` for `projects/segments/scripts`~~ Done.

**Tests required:** `tests/unit/test_segments_main_new_import.py` (new) -- imports the real module and confirms `main` is callable; does not call it (would authenticate to real BigQuery/Drive).

**Branch/PR/commit that fixes it:** `feature/safety-test-baseline` (this branch).
**Date resolved:** 2026-08-20

---

### IH-016
**Title:** `get_metadata` reads the loop variable after the loop ends
**Severity:** Low
**Status:** Fixed
**Date discovered:** 2026-08-19 (identical on main; file unchanged on this branch)

**Business impact:** If a campaign's metadata query returns zero rows (e.g. the code name was deleted or mistyped), the function raises an unhelpful `NameError` instead of a clear "campaign not found" error, and that `NameError` is then swallowed by IH-002.

**Technical explanation:** `get_metadata()` iterates `for row in metadata_raw: countries.append(row.country)`, then reads `end_date = row.end_date` (and several other fields) after the loop, relying on Python's loop-variable leakage. This also silently takes the last row's values without verifying all rows agree, though campaign-tracker writes one independently-editable row per country.

**Exact file and line evidence:**
- `projects/automation/query_orchestrator.py:203-221`, specifically `:209` -- `end_date = row.end_date` (outside the `for` block that starts at `:204`)

**How to reproduce / verify safely:**
```
python -m pytest tests/unit/test_get_metadata_empty_result.py -v
```
Calls the real `get_metadata()` against a `FakeBigQueryClient` returning zero rows and asserts it raises `ValueError` with a clear message, instead of the previous opaque `NameError`.

**Fix applied:** `projects/automation/query_orchestrator.py`'s `get_metadata()` now checks `if not countries:` immediately after the collection loop and raises `ValueError(f"No Campaign_Tracker rows found for code_name={codename!r}; cannot resolve campaign metadata.")` before reaching any post-loop `row.*` access. The second half of the recommended correction (validate that all per-country rows agree on shared fields) was **not implemented** -- deciding what to do on disagreement (raise? warn? prefer a specific row?) is a validation-design question, not a single-answer bug fix; left open for a follow-up.

**Recommended correction:** ~~Raise an explicit, descriptive error when `metadata_raw` is empty~~ Done. ~~Document (or enforce) that all per-country rows... agree~~ not implemented, see above.

**Tests required:** `tests/unit/test_get_metadata_empty_result.py` (new, 1 test).

**Branch/PR/commit that fixes it:** `feature/safety-test-baseline` (this branch).
**Date resolved:** 2026-08-20

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

### IH-017
**Title:** `[Common Queries]` recursion swaps date arguments (latent)
**Severity:** Medium
**Status:** Fixed
**Date discovered:** 2026-08-19 (identical on main; file unchanged on this branch)

**Business impact:** Currently none -- see below. The moment a date-window placeholder is added to any query under `[Common Queries]`, every one of those nine queries will silently run with the start/end dates inverted, with no error raised.

**Technical explanation:** `run_pipeline_queries` is declared as `(config, codename, end_date_q, start_date_q, countries, pipeline_type, bq_client, radiuses, ...)`. The top-level call (`run_by_codename`) passes `end_date_q, start_date_q` correctly into those slots. But the function's own recursive call for `"common_queries"` passes `start_date_q, end_date_q` -- transposed relative to its own parameter order.

**Exact file and line evidence:**
- `projects/automation/query_orchestrator.py:264-268` (parameter declaration order)
- `projects/automation/query_orchestrator.py:297-306` (the recursive call, arguments in the wrong order relative to the declaration)
- `projects/automation/query_orchestrator.py:413-424` (the correct top-level call, for contrast)
- Verified harmless today: `projects/automation/queries.ini:13-235` (`[Common Queries]`) contains zero `{start_date_q}`/`{end_date_q}` occurrences; the first such placeholder in the whole file is at line 255, inside `[Retail Intelligence]`.

**How to reproduce / verify safely:** `python -m pytest tests/unit/test_automation_build_query.py -v -k CommonQueriesDateSwap`. Two tests: the original placeholder-absence guard (kept as defense-in-depth), and a new test that directly calls the real `run_pipeline_queries` and intercepts the recursive call, asserting `end_date_q`/`start_date_q` arrive unswapped.

**Fix applied:** `projects/automation/query_orchestrator.py`'s recursive call (previously positional, in the wrong order) now passes every argument to `run_pipeline_queries` by keyword: `end_date_q=end_date_q, start_date_q=start_date_q, ...`. Switching to keyword arguments (rather than just reordering the positional ones) means a future parameter reorder in the function signature can no longer silently reintroduce this swap.

**Recommended correction:** ~~Fix the call to pass `(end_date_q, start_date_q)` in the correct order~~ Done, via keyword arguments.

**Tests required:** `tests/unit/test_automation_build_query.py::TestCommonQueriesDateSwapFixed` (renamed from `TestCommonQueriesDateSwapIsCurrentlyLatentNotActive`; keeps the original placeholder-absence test and adds `test_common_queries_recursive_call_preserves_date_argument_order`).

**Branch/PR/commit that fixes it:** `feature/safety-test-baseline` (this branch).
**Date resolved:** 2026-08-20

---

### IH-018
**Title:** Bare-date `BETWEEN` window drops the final day / UTC-vs-local-day skew
**Severity:** High
**Status:** Open
**Date discovered:** 2026-08-19 (identical on main; files unchanged on this branch)

**Business impact:** Every reporting window silently excludes most of its own final day's data, and the boundary is computed in UTC while device activity is bucketed by local day in GST-offset markets (UAE, KSA, etc.), shifting the effective window by several hours.

**Technical explanation:** `get_run_dates` returns plain `%Y-%m-%d` date strings, which are substituted into `BETWEEN "{start_date_q}" AND "{end_date_q}"` clauses. A bare date coerces to `00:00:00` at the start of that day, so `end_date_q` effectively means "up to midnight at the start of the end date," not through the end of it. Separately, `datetime.today()` is evaluated in whatever timezone the process runs in (UTC on Cloud Functions), while device timestamps are meant to represent local activity in markets offset from UTC.

**Exact file and line evidence:**
- `projects/automation/query_orchestrator.py:369-372` (bare `strftime("%Y-%m-%d")` return values)
- `projects/automation/query_orchestrator.py:344` -- `today = datetime.today()`
- Recurs at `projects/automation/queries.ini:255, 312-313, 458-459, 517-518, 649-650, 921-922` (`BETWEEN "{start_date_q}" AND "{end_date_q}"`)

**How to reproduce / verify safely:** Static reading of the date-string format and its use in `BETWEEN` clauses; `tests/unit/test_get_run_dates.py` covers the pure date-arithmetic side (clamps, floors) but does not itself execute SQL, since that would require BigQuery.

**Recommended correction:** Use full timestamps (or an explicit `< end_date_q + 1 day`) instead of bare dates in the `BETWEEN` clauses; make the timezone used for "today" explicit and match it to the markets' local day.

**Tests required:** `tests/unit/test_get_run_dates.py` (added, covers the pure-function side). A SQL-text test asserting the generated `BETWEEN` clause once the fix changes its shape.

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

### IH-019
**Title:** `time_interval` accepted but never used in `get_run_dates`
**Severity:** Low
**Status:** Open
**Date discovered:** 2026-08-19 (identical on main; file unchanged on this branch)

**Business impact:** Campaigns cannot actually configure their reporting cadence via `time_interval` beyond gating whether they are selected for a run at all -- the window width itself is a hardcoded 9 days for every campaign, regardless of what `time_interval` says.

**Technical explanation:** `get_run_dates(end_date, last_update, start_date, interval)` never references its `interval` parameter in its body; the 9-day lag is hardcoded via `timedelta(days=9)` in two places.

**Exact file and line evidence:**
- `projects/automation/query_orchestrator.py:340-346` (function signature includes `interval`, body never uses it)
- `projects/automation/variables.py:114-116` (the same 9-day lag duplicated as a magic number in the `q_update_status` SQL)
- `time_interval` is only used to gate selection: `projects/automation/variables.py:131-132`

**How to reproduce / verify safely:** `python -m pytest tests/unit/test_get_run_dates.py -v -k time_interval`

**Recommended correction:** Either use `interval` to size the window, or remove the parameter and document that the window is fixed at 9 days by design.

**Tests required:** `tests/unit/test_get_run_dates.py::test_time_interval_parameter_does_not_affect_the_result` (added, passing).

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

### IH-020
**Title:** `SELECT DISTINCT *` dedupe can destroy legitimate duplicate rows
**Severity:** Medium
**Status:** Open
**Date discovered:** 2026-08-19 (identical on main; `q_deduplicate_ber` unchanged, still called from the rewritten `upload_backend.py`)

**Business impact:** Two genuinely identical impression records (same device, same timestamp, same creative -- which can legitimately happen) are collapsed into one, silently undercounting real activity, as a side effect of a step meant only to remove accidental duplicates from reruns.

**Technical explanation:** `remove_dups()` runs `CREATE OR REPLACE TABLE ... AS SELECT DISTINCT * FROM ...`, which cannot distinguish "this row was inserted twice by a rerun" from "these two rows happen to have identical values." The schema (`schema_back_end`) has no unique key, so there is no way to tell the two cases apart with this approach.

**Exact file and line evidence:**
- `projects/automation/variables.py:151-160` (`q_deduplicate_ber`)
- `projects/automation/upload_backend.py:322` -- `remove_dups(bq_client, code_name)` (still called, confirmed present on this branch's rewritten file)

**How to reproduce / verify safely:** Static reading of the query and schema; a live reproduction requires a real BigQuery table with genuinely duplicate rows, out of scope offline.

**Recommended correction:** Add a synthetic row-level identity (e.g. a load batch id + source line number) so real duplicates from reruns can be distinguished from coincidentally-identical rows, then dedupe on that identity instead of `SELECT DISTINCT *`.

**Tests required:** None offline; a live-parity test comparing row counts before/after dedupe against a known-duplicate fixture is a candidate for a future integration-test tier.

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

### IH-021
**Title:** Backend-report file matching uses a Drive substring search
**Severity:** Medium
**Status:** Fixed
**Date discovered:** 2026-08-19 (identical on main; `search_files_in_folder`/`navigate_and_search_file` unchanged on this branch)

**Business impact:** A backend report id that is a substring of another report id (e.g. `1001` inside `21001_report.csv`) can match the wrong file, and -- combined with the append/dedupe flow -- merge another campaign's backend data into the wrong campaign's table.

**Technical explanation:** The Drive query uses `name contains '{file_prefix}'`, where `file_prefix` is a bare integer backend-report id with no delimiter anchoring.

**Exact file and line evidence:**
- `projects/automation/upload_backend.py:98` -- the Drive query string concatenates `file_prefix` into a `name contains '...'` clause with no anchoring.

**How to reproduce / verify safely:**
```
python -m pytest tests/unit/test_upload_backend_search_files.py -v
```
Two tests: the extracted `_file_name_starts_with_prefix` helper directly (`"21001_report.csv"` no longer matches prefix `"1001"`), and `search_files_in_folder` end-to-end against a fake Drive service returning both a true match and a substring-collision false positive, asserting only the true match survives.

**Fix applied:** `projects/automation/upload_backend.py`: extracted `_file_name_starts_with_prefix(name, file_prefix)` (a plain `str.startswith` check) and applied it as a post-filter on `search_files_in_folder()`'s results, after the (still necessarily broad, since Drive's query language has no anchored "starts with" operator) `name contains '{file_prefix}'` query. Chose the post-filter approach over `name = '<exact filename>'` (the recommended correction's first alternative) because the exact filename generally isn't known in advance -- only the prefix is; the post-filter matches the function's own documented intent ("start with a specific prefix") precisely.

**Recommended correction:** ~~Anchor the match... or validate that exactly one file matches before proceeding~~ Done, via a `startswith` post-filter.

**Tests required:** `tests/unit/test_upload_backend_search_files.py` (new, 2 tests) -- follows the audit's own suggestion to extract the logic into a testable function first.

**Branch/PR/commit that fixes it:** `feature/safety-test-baseline` (this branch).
**Date resolved:** 2026-08-20

---

### IH-022
**Title:** Stale external table reuse in `upload_backend.py`
**Severity:** Critical
**Status:** **Fixed** (already resolved on this branch prior to this audit -- not a fix produced by this branch's own work; recorded here for visibility, per the project's request to show what was already true when work started)
**Date discovered:** 2026-08-19 (this defect existed at the main baseline, c0f2e37)
**Date resolved:** Prior to this audit (present in dev at commit 296a157, "Fix: BER new column(s) drop" -- exact original fix date not independently determinable from the local clone's reflog)

**Business impact (as it existed at main):** A campaign's backend-report ingestion could silently insert an older Drive file's data whenever the external staging table `{backend_report}_new` already existed from an interrupted prior run.

**Technical explanation (historical, at main):** `insert_new_BER()` used to swallow BigQuery's `Conflict` exception when the staging table already existed, and proceed to insert from whatever that pre-existing table pointed at -- which could be the previous run's Drive file id, not the current one.

**What changed on this branch:** `insert_new_BER()` now explicitly deletes the `{backend_report}_new` table (`bq_client.delete_table(table_ref, not_found_ok=True)`) immediately before creating it, both on the happy path and inside the `except Conflict:` handler, guaranteeing the external table always points at the current run's Drive file.

**Exact file and line evidence:**
- `projects/automation/upload_backend.py:256-273` (delete-before-create in the happy path, and delete-and-recreate inside `except Conflict:`)
- Historical comparison: `git diff c0f2e3779c57de37aa48fa48b9edf92e4170b3cb HEAD -- projects/automation/upload_backend.py` shows the `except Conflict: print(...)`-only pattern replaced by explicit delete-then-recreate.

**How to reproduce / verify safely:** Static diff review, as above (no live BigQuery access needed to confirm the code change).

**Recommended correction:** None outstanding -- fixed. Recommend adding a regression test (see below) so this cannot silently regress.

**Tests required:** A characterization test asserting `insert_new_BER` always calls `delete_table` before `create_table`, using `tests/fakes/fake_bigquery.py` -- not yet written; flagged as a good first task for a follow-up branch, since `upload_backend.py` currently constructs its own BigQuery client rather than accepting an injectable one.

**Branch/PR/commit that fixes it:** Present at dev/296a157, inherited by feature/safety-test-baseline.

---

### IH-023
**Title:** `segments/main.py` `NameError` on undefined `bq_client`
**Severity:** Medium
**Status:** **Fixed** (already resolved on this branch prior to this audit)
**Date discovered:** 2026-08-19 (this defect existed at the main baseline, c0f2e37)
**Date resolved:** Prior to this audit (present in the uncommitted dev work now committed as 810e30b)

**Business impact (as it existed at main):** `projects/segments/main.py` could not run to completion at all -- it referenced `bq_client` while the line that would have defined it was commented out.

**What changed on this branch:** `main()` now calls `bq_client, drive_service = authenticate_get_clients()` unconditionally at the top of the function.

**Exact file and line evidence:**
- `projects/segments/main.py:47` -- `bq_client, drive_service = authenticate_get_clients()`
- Historical: at main baseline, this line was commented out while `bq_client` was still referenced later in the file.

**How to reproduce / verify safely:** Static diff review; `python -m py_compile projects/segments/main.py` (part of this branch's CI static-check step) confirms the file is at least syntactically valid, though a full NameError-style bug is a runtime issue that compilation alone cannot catch.

**Recommended correction:** None outstanding -- fixed.

**Tests required:** None specific (this was a straightforward variable-definition bug, not a logic error worth a dedicated regression test).

**Branch/PR/commit that fixes it:** Present in the uncommitted dev work, committed as 810e30b at the start of this branch's work.

---

### IH-024
**Title:** `push_to_bq.py` external staging table `Conflict`-swallow
**Severity:** Medium
**Status:** **Fixed** (already resolved on this branch prior to this audit)
**Date discovered:** 2026-08-19 (this defect existed at the main baseline, c0f2e37)
**Date resolved:** Prior to this audit (present in the uncommitted dev work now committed as 810e30b)

**Business impact (as it existed at main):** The same class of issue as IH-022, but for the per-segment CSV staging tables used during segment publication to BigQuery (`{code}_{country}_{segment}_served`-style tables), rather than the backend-report staging table.

**What changed on this branch:** `create_external_table()` now calls `delete_table(table_name, bq_client)` unconditionally immediately before `bq_client.create_table(table)`, removing any leftover staging table from a previous run before creating a fresh one.

**Exact file and line evidence:**
- `projects/segments/scripts/push_to_bq.py:107-109` -- `delete_table(table_name, bq_client)` called immediately before `table = bq_client.create_table(table)`
- Historical: at main baseline, table creation was wrapped in a bare `try/except:` that only printed a message on conflict, without deleting or recreating anything.

**How to reproduce / verify safely:** Static diff review.

**Recommended correction:** None outstanding -- fixed.

**Tests required:** None specific.

**Branch/PR/commit that fixes it:** Present in the uncommitted dev work, committed as 810e30b at the start of this branch's work.

---

## Security and access risks

### IH-025
**Title:** Flask UI has no authentication or CSRF protection on write routes
**Severity:** Critical
**Status:** Open
**Date discovered:** 2026-08-19 -- worse on this branch than at main: the write-capable route surface has grown.

**Business impact:** Anyone who can reach the UI's network port can trigger production BigQuery writes and Google Drive uploads, including a route that now runs the campaign tracker for every campaign in the system with a single unauthenticated request.

**Technical explanation:** No route in `ui/app.py` has an authentication decorator, a session check, or a CSRF token; no template renders a CSRF field; `Flask-WTF`/`CSRFProtect` is not installed or configured. On the main baseline there were two POST write routes (`/campaign/<code>/run/<action>`, `/automation`). This branch adds three more: `/api/campaign/<code>/run/<action>` (a JSON duplicate of the first), `/api/run-all-trackers` (loops over every campaign and calls the tracker for each, in one request), and `/api/campaigns/add` (currently does not persist -- see IH-041 -- but returns a fabricated success response).

**Exact file and line evidence:**
- `ui/app.py:119` -- `@app.route('/campaign/<code>/run/<action>', methods=['POST'])`
- `ui/app.py:154` -- `@app.route('/api/campaign/<code>/run/<action>', methods=['POST'])` (new on this branch)
- `ui/app.py:187` -- `@app.route('/api/run-all-trackers', methods=['POST'])` (new on this branch) -- loops `for code in campaigns.keys(): ... tracker_main(code)`
- `ui/app.py:215` -- `@app.route('/api/campaigns/add', methods=['POST'])` (new on this branch)
- `ui/app.py:284` -- `@app.route('/automation', methods=['POST'])`
- No occurrence of `csrf` (case-insensitive) anywhere under `ui/` (confirmed via repo-wide search)

**How to reproduce / verify safely:** Static reading of every `@app.route(...)` decorator and the absence of any auth/CSRF mechanism in the file; no live request was sent to any UI instance during this audit.

**Recommended correction:** Add authentication (even a simple shared-secret header would be an improvement) and CSRF protection before this UI is exposed on any network beyond `localhost`; treat `/api/run-all-trackers` as especially high-risk given its blast radius.

**Tests required:** Route-level tests asserting a 401/403 without credentials, once authentication is added (currently there is nothing to test -- every route is open by design/oversight).

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

### IH-026
**Title:** Flask app runs with `debug=True` on `host='0.0.0.0'`
**Severity:** Critical
**Status:** Fixed
**Date discovered:** 2026-08-19 (identical on main; unchanged on this branch)

**Business impact:** If this app is ever run outside a fully isolated local machine, the Werkzeug interactive debugger becomes reachable from the network, which can allow arbitrary code execution by anyone who can reach the port.

**Technical explanation:** `app.run(debug=True, host='0.0.0.0', port=5000)` binds to all network interfaces with the debugger enabled.

**Exact file and line evidence:**
- `ui/app.py:401` -- `app.run(debug=True, host='0.0.0.0', port=5000)`

**How to reproduce / verify safely:**
```
python -m pytest tests/unit/test_ui_app_safe_defaults.py -v
```
Parses `ui/app.py`'s source with `ast` (never imports or runs the module) and asserts `app.run()`'s `debug` and `host` keyword arguments. Static reading; the UI itself is not run during this fix, per this branch's safety boundary. Also verified with `python -m compileall -q ui/app.py` (syntax only).

**Fix applied:** `ui/app.py:401` -- `app.run(debug=True, host='0.0.0.0', port=5000)` -> `app.run(debug=False, host='127.0.0.1', port=5000)`. Matches the recommended correction exactly; this app is documented as "not deployed anywhere, a local dashboard" (`docs/modernization-spec.md` §1.5), so there is no known legitimate current use of network-wide binding to preserve -- if that assumption is wrong, flag it and this can be reverted or made configurable via an environment variable instead of a hardcoded default.

**Recommended correction:** ~~`debug=False` outside local development, bind to `127.0.0.1` unless a reverse proxy with its own auth sits in front.~~ Done.

**Tests required:** `tests/unit/test_ui_app_safe_defaults.py::TestUiAppSafeRunDefaults` (added after the fix, as a regression guard against this specific default being silently reintroduced -- not required to prove the original finding, since that was a config default, not a logic defect).

**Branch/PR/commit that fixes it:** `feature/safety-test-baseline` (this branch).
**Date resolved:** 2026-08-20

---

### IH-027
**Title:** Hardcoded Flask `secret_key` committed in source
**Severity:** High
**Status:** Open
**Date discovered:** 2026-08-19 (identical on main; unchanged on this branch)

**Business impact:** Anyone with read access to this repository can forge session cookies and flash-message state for the UI.

**Technical explanation:** The Flask session-signing key is a literal string in source rather than an environment variable or secret.

**Exact file and line evidence:**
- `ui/app.py:26` -- `app.secret_key = 'info-harbor-secret-key-2024'`

**How to reproduce / verify safely:** Static reading.

**Recommended correction:** Load from an environment variable or Secret Manager; rotate the key once moved.

**Tests required:** None.

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

### IH-028
**Title:** `delete_from_drive.py` ships with `DELETE_MODE = True` by default
**Severity:** High
**Status:** In Progress
**Date discovered:** 2026-08-19 -- present at main under a different folder id; the file was substantially rewritten on this branch (622 lines changed) but the armed-by-default pattern was carried forward unchanged.

**Business impact:** Running this script with no arguments permanently deletes files from a hardcoded Google Drive folder, with no confirmation prompt and no dry-run default.

**Technical explanation:** The module-level constants `DELETE_MODE` and the target folder id are hardcoded, and `DELETE_MODE` defaults to `True` (destructive), not `False` (dry run).

**Exact file and line evidence:**
- `projects/segments/scripts/delete_from_drive.py:31` -- `FOLDER_ID_TO_DELETE = "1tTawCZ4ihAfDeKp1Xac9QiDIBICfmMuM"` (a different folder id than at the main baseline, confirming this file was reworked, not merely reformatted)
- `projects/segments/scripts/delete_from_drive.py:34` -- `DELETE_MODE = True`
- `projects/segments/scripts/delete_from_drive.py:38` -- `DELETE_ALL_FILES = False`

**How to reproduce / verify safely:**
```
python -m pytest tests/unit/test_delete_from_drive_safe_default.py -v
```
`ast`-parses the source and confirms the module-level `DELETE_MODE` assignment is `False`. Deliberately does not import the module (still on the "never run/never import" boundary) -- this script was not run or imported during this fix either.

**Fix applied (partial):** `projects/segments/scripts/delete_from_drive.py:34`: `DELETE_MODE = True` -> `DELETE_MODE = False`. **Not implemented:** an explicit `--yes`/`--confirm` CLI flag, and taking the folder id as a required argument instead of a hardcoded constant -- both are real feature additions (this script currently has no argument parsing at all) with their own design surface, not single-answer fixes. Added to the decision queue rather than guessed here.

**Recommended correction:** ~~Default `DELETE_MODE` to `False`~~ Done. ~~require an explicit --yes/--confirm CLI flag... take the folder id as a required argument~~ not implemented, see decision queue.

**Tests required:** `tests/unit/test_delete_from_drive_safe_default.py` (new, 1 test) -- narrower than "once refactored to accept flags" (no refactor was done), but closes the immediate default-safety gap with a regression guard.

**Branch/PR/commit that fixes it:** `feature/safety-test-baseline` (this branch) -- partial (default flip only).
**Date resolved:** N/A -- CLI confirmation flag and required folder-id argument remain open

---

### IH-029
**Title:** Inconsistent credential model (key files vs. Secret Manager)
**Severity:** Medium
**Status:** Open
**Date discovered:** 2026-08-19 (identical on main; pattern unchanged on this branch)

**Business impact:** Two different trust models coexist for the same system: the deployed Cloud Function fetches credentials from Secret Manager at runtime, while the UI, the segments scripts, and several standalone tools read long-lived service-account JSON key files from a local `keys/` directory. The key-file path is a weaker, harder-to-rotate model that this modernization should converge away from.

**Technical explanation:** `shared/config/campaigns/database_loader.py` (used by the Flask UI on every page load) and most of `projects/segments/scripts/` read `service_account.Credentials.from_service_account_file(...)` against files under `keys/`, while `projects/automation/main.py` and `custom_codename.py` fetch secrets from Secret Manager (`secretmanager.SecretManagerServiceClient`).

**Exact file and line evidence:**
- `shared/config/campaigns/database_loader.py:21-25` (key-file path, used by the UI's `get_live_campaigns()`)
- `projects/automation/main.py:14-17, 110-118` (Secret Manager path)
- `keys/` exists locally on this machine (confirmed by directory listing -- names only, contents never read) and is git-ignored (`.gitignore:39` -- `keys/`), so it is not committed, but its existence is required for the key-file code paths to function at all.

**How to reproduce / verify safely:** Static reading of both code paths; the local `keys/` directory's file names were listed to confirm it is untracked and gitignored, but no file contents were opened.

**Recommended correction:** Converge on Secret Manager (or another centrally-rotatable secret store) for every code path, including the UI and segments scripts.

**Tests required:** None offline; this is an architecture decision, not a bug with a unit-testable fix.

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

### IH-030
**Title:** Unparameterized SQL and Drive query-string interpolation throughout
**Severity:** High
**Status:** Open
**Date discovered:** 2026-08-19 (identical on main; pattern present throughout both baseline and branch code)

**Business impact:** No query anywhere in this codebase uses parameterized SQL; every value (including some that could originate from user-editable metadata like campaign names) is interpolated directly into a SQL or Drive-API query string. A campaign name containing an apostrophe breaks the query outright today; a more deliberately crafted value could inject additional SQL or Drive query clauses.

**Technical explanation:** `bigquery.ScalarQueryParameter` (BigQuery's parameterized-query mechanism) does not appear anywhere in the repository. Every `INSERT`/`UPDATE`/`SELECT` is built via f-strings or `.replace()` substitution.

**Exact file and line evidence:**
- `projects/campaign-tracker/main.py:39-68` -- campaign name and dates interpolated directly into an `INSERT`
- `projects/segments/scripts/query_orchestrator.py:197-204` -- POI filter values interpolated into a quoted SQL `IN (...)` list
- `projects/automation/upload_backend.py:89, 98` -- Drive `q=` search strings built via f-string interpolation of `folder_name`/`file_prefix`
- `projects/segments/scripts/transfer_to_drive.py:56-57` -- Drive folder-search query built the same way
- `projects/segments/scripts/delete_from_drive.py` (multiple sites, feeding a delete path -- see IH-028)

**How to reproduce / verify safely:** Static reading; no injection attempt was made against any live service.

**Recommended correction:** Move every BigQuery call to parameterized queries; for Drive query strings, at minimum escape single quotes in interpolated values.

**Tests required:** A unit test asserting a campaign name containing an apostrophe is safely escaped, once query construction is centralized enough to test in isolation.

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

## Data-correctness and idempotency risks

*IH-007, IH-008, IH-009, IH-011, IH-012, and IH-020 above are also data-correctness/idempotency findings; they are filed under "Confirmed defects" because each is tied to a specific, narrow code defect. The two findings below are filed separately because they describe an idempotency property of the pipeline's write pattern as a whole, not a single line-level bug.*

### IH-031
**Title:** `{codename}_visitors` uses `WRITE_APPEND` with an overlapping window
**Severity:** High
**Status:** Open
**Date discovered:** 2026-08-19 (identical on main; file unchanged on this branch)

**Business impact:** Every query except `visitors` truncates and rewrites its destination table on each run, but `visitors` appends -- and because `get_run_dates` deliberately re-queries a window that overlaps the previous run's (`start_date_q = last_update - 9 days`), consecutive runs duplicate rows in this table on the normal, successful path, not just on error-triggered reruns.

**Technical explanation:** `run_pipeline_queries` sets `WRITE_TRUNCATE` for every query except `"visitors"`, which uses `WRITE_APPEND`. Combined with the 9-day look-back built into `get_run_dates` (see IH-018/IH-019), each successful run re-fetches and re-appends several days already covered by the previous run.

**Exact file and line evidence:**
- `projects/automation/query_orchestrator.py:329-332` -- sets `WRITE_TRUNCATE` for every query except `visitors`, which gets `WRITE_APPEND`
- `projects/automation/query_orchestrator.py:353` -- `start_date_q = last_update - timedelta(days=9)`

**How to reproduce / verify safely:** Static reading of the write-disposition logic and the date-window construction together; live reproduction requires two real BigQuery runs, out of scope offline. `tests/unit/test_get_run_dates.py` independently confirms the window is deliberately backdated relative to `last_update` on every call.

**Recommended correction:** Either dedupe on load (with a real row identity, not `SELECT DISTINCT *` -- see IH-020), or switch to a `MERGE`/upsert pattern keyed on a natural row identity.

**Tests required:** A parity test comparing row counts in `{codename}_visitors` before and after a rerun, using the parity manifest helpers in `tests/parity/manifest.py` (needs a fake/sandboxed BigQuery table to be meaningful; flagged for a future integration-test tier).

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

### IH-032
**Title:** Combined `{code_name}_Segments` table appended without dedupe on rerun
**Severity:** Medium
**Status:** Open
**Date discovered:** 2026-08-19 (identical on main; pattern unchanged on this branch, even though the external staging table creation around it was fixed -- see IH-024)

**Business impact:** While IH-024 fixed the staging-table-conflict problem, the final `INSERT INTO {code_name}_Segments` step that follows it is still a plain append with no dedupe, so rerunning `push_to_bq.py`'s combined-table step for the same campaign duplicates every DID/segment/country/controlled row already inserted.

**Technical explanation:** `insert_to_combined()` always executes a plain `INSERT INTO ... SELECT ...` against the combined table; nothing truncates or dedupes it between runs, unlike the external staging table it reads from (which IH-024 now deletes-and-recreates each time).

**Exact file and line evidence:**
- `projects/segments/scripts/push_to_bq.py:54-87` (`insert_to_combined`, plain `Insert INTO` with no `WRITE_TRUNCATE`-equivalent or existence check on the combined table)
- `projects/segments/scripts/push_to_bq.py:35-51` (`create_Combined_table`, only creates the table once via a bare `except:` if it already exists -- it is never truncated on rerun)

**How to reproduce / verify safely:** Static reading; live reproduction requires a real BigQuery table, out of scope offline.

**Recommended correction:** Truncate the combined table before each full rerun of a campaign's segment publication, or key inserts so reruns are naturally idempotent (e.g. delete existing rows for that DID/segment/country combination before inserting).

**Tests required:** A parity test on row counts before/after a rerun, same caveat as IH-031 (needs a fake or sandboxed BigQuery table).

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

## Performance issues

### IH-033
**Title:** O(lines) redundant Drive upload calls in the old `transfer_to_drive.py`
**Severity:** Low
**Status:** **Fixed** (already resolved on this branch prior to this audit)
**Date discovered:** 2026-08-19 (this defect existed at the main baseline, c0f2e37)
**Date resolved:** Prior to this audit (present in the uncommitted dev work now committed as 810e30b)

**Business impact (as it existed at main):** The old upload loop called `file.SetContentFile(file_path)` once per line of every uploaded CSV, inside a loop whose body was otherwise a no-op (the actual upload happened once, after the loop, via `file.Upload()`) -- pure wasted CPU proportional to file size, worsening with campaign scale.

**What changed on this branch:** `transfer_to_drive.py` was rewritten to use `googleapiclient`'s `MediaFileUpload`, with resumable, chunked upload for files over 5 MB and simple single-shot upload otherwise -- no per-line work at all. This also removed the file's dependency on `pydrive2`/`oauth2client` in favor of the same Google API client library used elsewhere in the repo, and added explicit handling for Drive storage-quota-exceeded errors (returning partial progress instead of crashing).

**Exact file and line evidence:**
- `projects/segments/scripts/transfer_to_drive.py:107-203` (the rewritten `transfer()` function; contrast with the historical version's per-line `SetContentFile` loop, visible via `git show c0f2e3779c57de37aa48fa48b9edf92e4170b3cb:projects/segments/scripts/transfer_to_drive.py`)

**How to reproduce / verify safely:** Static diff review.

**Recommended correction:** None outstanding for the performance issue itself. Note that IH-011 (duplicate uploads on rerun) is a separate, still-open defect in this same file.

**Tests required:** None specific to the performance fix.

**Branch/PR/commit that fixes it:** Present in the uncommitted dev work, committed as 810e30b at the start of this branch's work.

---

## Deployment and operational risks

### IH-034
**Title:** CI deploys to production on every push to `main`, no tests, no gate
**Severity:** High
**Status:** Open
**Date discovered:** 2026-08-19 (identical on main; `.github/workflows/deploy.yml` byte-for-byte unchanged on this branch)

**Business impact:** Any push to `main` -- with no test run, no required review, no approval gate -- immediately redeploys the production Cloud Function using a long-lived service-account key.

**Technical explanation:** The workflow triggers on `push: branches: [main]`, has exactly three steps (checkout, auth, deploy), and none of them run a test suite. This branch adds a separate, non-deploying PR-validation workflow (`.github/workflows/pr-validation.yml`) alongside the existing one, per the explicit instruction not to remove or modify `deploy.yml` in this branch.

**Exact file and line evidence:**
- `.github/workflows/deploy.yml:3-6` -- `on: push: branches: [main]`
- `.github/workflows/deploy.yml:12-34` -- checkout, gcloud auth via `secrets.GCP_SA_KEY`, then `gcloud functions deploy` with no preceding test step

**Why this should be replaced (not done in this branch):** A safe sequence would be: (1) require `pr-validation.yml`'s offline suite to pass before a PR can merge to `main` (branch protection, a repository setting, not a code change); (2) gate the deploy job on that same test job within one workflow, or make `deploy.yml` a `workflow_run` triggered only after `pr-validation.yml` succeeds; (3) move off a long-lived `GCP_SA_KEY` secret toward Workload Identity Federation. None of this is done here -- it requires GitHub repository settings and Google Cloud IAM changes, both explicitly out of this branch's safety boundary (no deploy, no GCP access, no production writes).

**How to reproduce / verify safely:** Static reading of `deploy.yml`; the new `pr-validation.yml` was verified to run correctly (see Validation section of `docs/modernization-log.md`) without ever calling `gcloud` or authenticating to GCP.

**Recommended correction:** See "Why this should be replaced" above.

**Tests required:** None (a CI/process change, not a code defect).

**Branch/PR/commit that fixes it:** Not yet fixed; `pr-validation.yml` (this branch) is a prerequisite step, not the fix itself.
**Date resolved:** N/A

---

### IH-035
**Title:** `pandas` imported by `data_validation.py` but undeclared in deployed requirements
**Severity:** Low
**Status:** Fixed
**Date discovered:** 2026-08-19 (identical on main; both files unchanged on this branch)

**Business impact:** `data_validation.py` sits inside `projects/automation/` (the directory Cloud Functions deploys from) but is not imported by `main.py`, so the deployed function does not currently break -- but the moment anyone imports it from a reachable code path, the deploy will fail at runtime with `ModuleNotFoundError: No module named 'pandas'`.

**Technical explanation:** `projects/automation/requirements.txt` (the file Cloud Functions actually installs from, per `--source projects/automation` in `deploy.yml`) does not list `pandas`, while `data_validation.py` imports it.

**Exact file and line evidence:**
- `projects/automation/data_validation.py:23` -- `import pandas as pd`
- `projects/automation/requirements.txt` -- 10 pins, no `pandas` entry (confirmed by listing the file's contents)
- Root `requirements.txt` (not what gets deployed) does include `pandas==2.1.1`

**How to reproduce / verify safely:**
```
python -m pytest tests/unit/test_automation_requirements.py -v
```
Static text check: confirms `data_validation.py` still imports `pandas` and that `projects/automation/requirements.txt` declares it. No deploy was performed.

**Fix applied:** Added `pandas==2.1.1` to `projects/automation/requirements.txt` (pin matches the root `requirements.txt`'s existing pin, so no new version introduced). The other imports in `data_validation.py` (`requests`, `google.oauth2.service_account` via `google-auth`, `googleapiclient.discovery` via `google-api-python-client`) were checked and are already declared. Did not remove `data_validation.py` from the deployed source directory (the recommended correction's other option) -- it is a standalone script not imported by `main.py`, so leaving it in place with a correct dependency is the smaller, non-destructive change.

**Recommended correction:** ~~Add `pandas` ... to `projects/automation/requirements.txt`~~ Done. A general CI check diffing all imports under `projects/automation/` against the requirements file (the audit's broader suggestion) was not added -- out of scope for this single-finding fix.

**Tests required:** `tests/unit/test_automation_requirements.py` (new) -- a narrow, targeted regression guard for this specific import/requirement pair, not the general CI linter described above.

**Branch/PR/commit that fixes it:** `feature/safety-test-baseline` (this branch).
**Date resolved:** 2026-08-20

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

### IH-036
**Title:** `projects/poi/` added with no tests, no CI wiring, no prior documentation
**Severity:** Medium
**Status:** Needs Validation
**Date discovered:** 2026-08-19 -- entirely new on this branch relative to the main baseline (commit `8981f83`, "Add: POI source code")

**Business impact:** A new standalone data-write module (POI = points of interest) exists in the repository with its own BigQuery write logic, but it is not exercised by any test, not deployed by CI, and not referenced by any other part of the system -- its correctness and intended usage are currently unverified by this audit.

**Technical explanation:** `projects/poi/main.py` defines its own `create_client`, `get_country_id`, `get_city_id`, `table_exists`, `create_poi_table`, `get_max_poi_id`, `insert_pois`, and `process_pois` functions, following the same `from variables import *` / `from input import *` pattern as the rest of the legacy code. A repository-wide search confirms nothing outside `projects/poi/` itself imports or references it, and `.github/workflows/deploy.yml` only deploys `projects/automation`.

**Exact file and line evidence:**
- `projects/poi/main.py:1-222` (full file, self-contained)
- `projects/poi/input.py`, `projects/poi/variables.py` (its own config, not shared with other projects)
- Confirmed via `grep -rn "projects.poi\|projects/poi\|from poi\|import poi"` across all tracked `.py` files: no hits outside `projects/poi/` itself

**How to reproduce / verify safely:**
```
python -m pytest tests/unit/test_poi_main_import.py -v
```
Confirms `projects/poi/main.py` imports cleanly and exposes its 8 documented functions. Static reading and a repository-wide grep were also performed (both already done, unchanged); the module's actual BigQuery write correctness still was not evaluated in depth (would require live credentials).

**Progress:** Added the smoke-import test the recommended correction suggested. Still **not decided**: whether `projects/poi/` should be wired into CI/tests as a first-class component or remain an intentionally standalone manual tool -- added to the decision queue, since it's a scope/ownership question, not a code defect. Remains **Needs Validation** overall: this test only proves the module *imports*, not that its BigQuery write logic is correct.

**Recommended correction:** Document its intended purpose (done, `docs/modernization-spec.md` §1.4); ~~add at least a smoke-import test~~ done; ~~decide whether it should be wired into CI/tests~~ not decided, see decision queue.

**Tests required:** `tests/unit/test_poi_main_import.py` (new, 1 test).

**Branch/PR/commit that fixes it:** N/A (this is a scope/documentation gap, not a bug to "fix").
**Date resolved:** N/A

---

## Missing tests and documentation

### IH-037
**Title:** No test suite existed; `.gitignore`'s `test*` pattern actively blocked one
**Severity:** Critical
**Status:** **Fixed** (by this branch)
**Date discovered:** 2026-08-19
**Date resolved:** 2026-08-19

**Business impact (before this branch):** The repository had zero tests, zero test configuration, and -- worse than merely absent -- an active `.gitignore` rule that would have silently discarded any `tests/` directory or `test_*.py` file a future contributor tried to commit, making the omission self-perpetuating.

**Technical explanation:** `.gitignore` contained a bare `test*` pattern with no exceptions, matching any path starting with `test` at any depth, including a `tests/` directory.

**Exact file and line evidence (before the fix, at main/dev prior to this branch):**
- `.gitignore:45` -- `test*` (the sole content of that section)

**What changed on this branch:**
- `.gitignore`'s `test*` line replaced with narrow, non-blocking patterns for test artifacts only (`.pytest_cache/`, `.coverage`, `htmlcov/`, `tests-output/`) plus a `.venv/` entry for this branch's local test tooling virtualenv -- `tests/` and every `test_*.py` are now tracked normally.
- Added `tests/` with `conftest.py`, `unit/`, `fakes/`, `fixtures/`, `parity/` (50 tests total, all passing offline).
- Added `pytest.ini` and `requirements-dev.txt`.

**How to reproduce / verify safely:**
```
git check-ignore -v tests/conftest.py
```
now exits 1 (not ignored); before the fix it matched `test*` and exited 0 (ignored). Also verified in `pr-validation.yml`'s static-checks job.

**Recommended correction:** None outstanding.

**Tests required:** N/A (this finding is about test infrastructure itself).

**Branch/PR/commit that fixes it:** `feature/safety-test-baseline` (this branch).
**Date resolved:** 2026-08-19

---

### IH-038
**Title:** `projects/poi/` was undocumented prior to this branch
**Severity:** Low
**Status:** **Fixed** (by this branch, documentation only)
**Date discovered:** 2026-08-19
**Date resolved:** 2026-08-19

**Business impact:** A new module with its own BigQuery write path existed with no mention in any spec or README, making it invisible to anyone reviewing the system's overall shape.

**What changed on this branch:** `docs/modernization-spec.md` now includes `projects/poi/` in its current-state workflow description and explicitly notes its undetermined integration status (cross-referenced to IH-036).

**Exact file and line evidence:** See `docs/modernization-spec.md`, "Current three-stage workflow" section (now four-stage, poi noted as a standalone addition).

**Recommended correction:** None outstanding for documentation; IH-036's code-level questions remain open.

**Tests required:** N/A.

**Branch/PR/commit that fixes it:** `feature/safety-test-baseline` (this branch).
**Date resolved:** 2026-08-19

---

## Suspected issues requiring validation

*These are plausible but not confirmed by this audit. They are listed separately, per instruction, so they are never mistaken for confirmed defects.*

### IH-039
**Title:** `aaa` file may indicate repository/production drift
**Severity:** Medium
**Status:** Needs Validation
**Date discovered:** 2026-08-19

**What is known:** A file named `aaa` sits at the repository root containing four lines of captured stdout: two `Starting queries for 123:` lines and two Python dict reprs with keys `'Executed Queries'` and `'Skipped Queries'`. Those exact key strings do not appear anywhere in this repository's current source (confirmed via repository-wide search).

**What is NOT established:** Whether this reflects a genuinely different, currently-deployed version of the orchestrator, or is simply a stray local log from an experiment, an abandoned branch, or a colleague's machine. Per explicit correction to this audit's framing: this file is a possible drift indicator, not proof of drift.

**How to validate safely:** Compare the deployed Cloud Function's source (via `gcloud functions describe`/`gcloud functions logs`, read-only, by someone with appropriate GCP access -- out of scope for this offline audit) against the commit history of this repository, to determine whether the deployed code matches any commit here. If it does, this file is almost certainly stray local output and can simply be deleted. If it does not, the parity/compatibility work in `docs/modernization-spec.md` needs to account for a real gap between this repository and production.

**Recommended correction:** No code change; a validation task for whoever has GCP read access, tracked here until resolved.

**Branch/PR/commit that fixes it:** N/A.
**Date resolved:** N/A

---

### IH-040
**Title:** Unexplained `keys/test-google-sheet.json` credential file
**Severity:** Low
**Status:** Needs Validation
**Date discovered:** 2026-08-19

**What is known:** The local (gitignored, untracked) `keys/` directory contains three files: `maddictdata-bq.json`, `maddictdata-google-sheets.json`, and `test-google-sheet.json`. Only the file names were listed; no file contents were opened or read as part of this audit, per the safety boundary against handling real credentials.

**What is NOT established:** What `test-google-sheet.json` is for, whether it represents a real (if lower-privilege) service account, whether any code path references it, and whether it should exist at all.

**How to validate safely:** Whoever manages this machine's `keys/` directory should confirm the purpose of that file and, if it is unused, remove it, without ever pasting its contents into any AI tool or issue tracker.

**Recommended correction:** None from this audit; a local hygiene question outside the repository itself (the file is not tracked by git).

**Branch/PR/commit that fixes it:** N/A.
**Date resolved:** N/A

---

### IH-041
**Title:** `/api/campaigns/add` reports success without persisting anything
**Severity:** Low
**Status:** Needs Validation
**Date discovered:** 2026-08-19 -- new route on this branch

**What is known:** `api_add_campaign()` validates the submitted campaign data via `CampaignConfig.validate()` and returns a JSON success response describing the "added" campaign, but the code contains an explicit `# TODO: Implement actual database save` comment and never writes anywhere.

**Exact file and line evidence:**
- `ui/app.py:263-265` -- the `# TODO: Implement actual database save` comment, immediately followed by a `return jsonify({'success': True, ...})`

**What is NOT fully established:** Whether this is a known, intentional stub (e.g. UI development ahead of backend work) or a genuinely misleading response that could confuse an operator into believing a campaign was created. Filed as Needs Validation rather than a confirmed defect because the code's own comment suggests this is understood, in-progress work, not an oversight -- but it is still worth surfacing since the HTTP response gives no indication that nothing was saved.

**Recommended correction:** Either implement the persistence, or change the response to make the stub status explicit (e.g. `"success": false, "error": "not yet implemented"`) until it does.

**Tests required:** A test asserting the route's response accurately reflects whether persistence occurred, once implemented.

**Branch/PR/commit that fixes it:** Not yet fixed.
**Date resolved:** N/A

---

### IH-042
**Title:** `.gitignore` fix revealed a previously-hidden, untracked, live-credential test script
**Severity:** Medium
**Status:** Needs Validation
**Date discovered:** 2026-08-19 -- discovered as a direct side effect of fixing IH-037

**What is known:** After narrowing `.gitignore`'s `test*` pattern (IH-037),
`git status` revealed a file that was previously silently excluded:
`projects/automation/test_backend_upload.py` (161 lines, untracked). It is a
manual smoke-test script for `upload_backend.py` that authenticates directly
with real BigQuery and Secret Manager credentials -- it is not part of the
offline suite added by this branch, and it was never run as part of this
audit. This is concrete evidence of what the old `test*` pattern was
actually hiding, beyond the abstract risk described in IH-037.

**What is NOT established:** Whether this script is still needed, whether
it should be committed (under a name/location that doesn't collide with the
new `tests/` convention), or whether it should be deleted. It touches
production credentials, so it is left completely untouched by this branch.

**Exact file and line evidence:**
- `projects/automation/test_backend_upload.py` (entire file, untracked;
  confirmed via `git status --porcelain` after the `.gitignore` fix)

**How to validate safely:** A human with knowledge of this script's history
should decide whether to commit it (e.g. renamed to avoid the `tests/`
convention, such as `scripts/manual_smoke_test_backend_upload.py`), delete
it, or leave it untracked deliberately. Do not run it -- it requires real
production credentials.

**Recommended correction:** None from this audit; a human decision, not a
code fix.

**Branch/PR/commit that fixes it:** N/A.
**Date resolved:** N/A
