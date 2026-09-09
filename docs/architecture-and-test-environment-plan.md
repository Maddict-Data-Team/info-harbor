# Architecture and Test-Environment Plan

**Status:** Accepted direction; implementation has not started.

**Purpose:** Define the target repository shape, the production-read/test-write
boundary, and the phased delivery gates for Info-Harbor. This plan supplements
`docs/modernization-spec.md`; where the two documents differ, this document
records the newer agreed direction pending a later, dedicated update to the
modernization specification.

## Decisions

- Keep one Git repository, with two applications built on one shared core.
- Keep the Flask UI. It becomes the operations application rather than being
  replaced.
- Preserve existing production BigQuery sources and Power BI-facing production
  marts. Refactoring is not permission to rename, move, or change their data.
- Use `dev` as the reviewed integration and test branch. `main` remains the
  production-release branch.
- Put common business code in a deliberately named package. Do not create a
  catch-all `utils` or `common` directory for unrelated code.
- Keep local secrets outside version control. Track only `.env.example` files
  containing variable names and safe examples; never keys or actual values.
- Use a separate non-production GCP project for test writes. Production source
  data may be read only when explicitly allowed by the test service identity.
- Name published test endpoints and Power BI/data-mart tables with `_test`.
  Put temporary tables in a dedicated test staging dataset with expiration,
  rather than treating them as published marts.
- Add structured, redacted, per-application logging and a run audit record.

## Target repository structure

This is the destination, not a request to move every file at once.

```text
apps/
  automation_service/        Cloud Function adapter and scheduler entry point
  operations_web/            Flask UI, UI routes, and UI-specific templates
packages/
  infoharbor_core/
    config/                  Typed environment, source, and output settings
    domain/                  Campaign and run data models
    services/                Campaign, POI, segment, and reporting workflows
    repositories/            Campaign metadata and other persistence contracts
    integrations/            BigQuery, Drive, and runtime-identity adapters
    queries/                 Named SQL templates and safe query construction
    validation/              Input, schema, and data-quality checks
    observability/           Logging, redaction, run context, and audit events
    utilities/               Small, pure, cross-domain helpers only
deploy/                      Explicit build/package definitions
tests/
  unit/                      Pure offline tests
  integration/               Opt-in tests against the test GCP project
  parity/                    Production-compatible output comparisons
  fakes/                     In-memory BigQuery and Drive substitutes
docs/
```

`utilities/` has a narrow purpose: a helper belongs there only when it has no
business-domain meaning, no I/O, and is genuinely used by more than one area.
For example, campaign table-name policy belongs in `config/` or `domain/`, not
in `utilities/`.

## Configuration model

The user-facing idea is correct: define stable shared variables once, then use
only the settings required by the page or workflow. The distinction is:

- `EnvironmentSettings` holds deployment identity, logging, and allowed
  projects.
- `SourceCatalog` holds production-read-only source locations.
- `OutputCatalog` holds the environment-specific output and staging locations.
- `CampaignConfig` holds one campaign's inputs such as countries, dates, POIs,
  segments, and report mode.
- Each UI page or command receives the relevant `CampaignConfig` and services;
  it does not import global values from a neighbouring application's
  `input.py`.

This preserves component-specific behavior during migration. A single module
must not silently collapse values that currently differ between Automation,
Segments, POI, and Campaign Tracker.

## Test environment boundary

Use placeholders until a human creates the resources:

```text
Production read-only project: maddictdata
Test write project:            <GCP_TEST_PROJECT_ID>
Test Drive root:               <TEST_DRIVE_FOLDER_ID>
```

The test service identity should have read-only access to the approved source
tables in `maddictdata`, permission to create query jobs, and write access only
to the test project and test Drive root. Exact IAM roles must be reviewed by
the GCP owner before provisioning.

Every test run must fail before issuing a cloud request when any of these are
true:

- the configured output project is `maddictdata`;
- a published test table does not end in `_test`;
- the source table is not on the allowlist;
- the run requests a production Drive folder;
- the environment is not explicitly `test`.

The test run should carry a generated `run_id`. It must write an audit row to
`<test-project>.Metadata.Campaign_Runs_test` with the application, campaign
code, resolved inputs, output locations, status, timing, and an error summary.
Never record credentials, access tokens, raw device identifiers, or full SQL
parameters containing sensitive values in logs or audit records.

## Static BigQuery inventory

The following inventory was derived by static inspection only. It is not a
cloud inventory and must be checked by the GCP owner before provisioning.

### Production read-only sources

- `maddictdata.Location_Signals.{country}_Data`
- `maddictdata.Location_Signals.device_os_mapping`
- `maddictdata.Automated_HWG.Home_Graph_Cumulative`
- `maddictdata.Automated_HWG.Work_Graph_Cumulative`
- `maddictdata.Automated_HWG.All_Pols_Mapping`
- `maddictdata.Back_End_Footfall.Lookup_Behavior`
- `maddictdata.Lookups.lu_date`, `lu_country`, and `lu_city`
- `maddictdata.POI_DB_{country_db}.All_POIs_{country}`
- `maddictdata.POI_DB_{country_db}.Behavioral_{country}_RAW_Cumulative`
- `maddictdata.Recurring_Segments.{country}_HNWI`

Country database substitutions are KSA, UAE, QTR for QAT, KWT, OMN, BHR, EGP
for EGY, and MAR. Application support differs today: Automation supports six
countries; Segments adds EGY; POI and Campaign Tracker also include MAR. The
migration must preserve those boundaries unless a separate feature expands
them.

### Test control and published output tables

Create test counterparts in `<GCP_TEST_PROJECT_ID>`:

- `Metadata.Campaign_Tracker_test` — required because Automation updates
  campaign status and `last_update`; it must never update production metadata.
- `Metadata.Campaign_Runs_test` — new test audit table.
- `Back_End_Footfall.<code>_pois_test`.
- `Back_End_Footfall.<code>_{query_name}_test`, where `query_name` is one of:
  `visitors`, `visitors_before`, `home_graph`, `travel_distance`,
  `travel_distance_km`, `dwell_time`, `loyalist_vs_onetime`, `device_os`,
  `employee_vs_visitor`, `behavior`, `socioeco`,
  `visitors_in_competitors`, `footfall`, `reaction_time`, `share_of_volume`,
  `footfall_week`, or `overlap_ooh`.
- `Back_End_Footfall.<code>_streach_test` — currently consumed by the OOH
  query, but this repository does not contain its producer. Do not enable the
  OOH test flow until its origin and schema are confirmed.
- `Placelift_Campaign_Segments.<code>_Segments_test`.
- `Back_End_Reports.<code>_test`.

External and CSV-backed tables are staging resources, not Power BI marts. Put
them in a dedicated test staging dataset with a short TTL and a unique run ID.
This is necessary because the current segment staging-name parser expects its
final token to identify served or controlled data; appending `_test` to every
temporary table would break that contract.

Configured-but-unreferenced items, including `District_Mapping`,
`Metadata.Placelift`, and `Metadata.test`, are intentionally excluded until a
consumer is identified.

## Observability

Each application emits structured logs with these minimum fields:

```text
timestamp, service, environment, run_id, campaign_code, operation,
status, duration_ms, error_type
```

Use one logger namespace per application (`automation`, `operations_web`,
`segments`, `poi`, and `campaign_tracker`) and a shared redaction layer. Local
logs may be separated by service file; cloud logs are separated by service and
environment labels. Error responses must include the run ID but not sensitive
details.

## Delivery phases and gates

### Phase A — contract foundation (not runtime enforcement)

Commit this plan only after review. Add offline tests for environment parsing,
source allowlisting, output-name generation, and redaction. No cloud resources
or production behavior change. These additive modules are deliberately not
connected to a live client or entry point in this phase: passing their tests
defines the required policy but does not by itself enforce it at runtime.

### Phase B — configuration boundary

Introduce typed source/output environment configuration alongside legacy
configuration, then wire its refusal gates into every client-creation and
write path before any cloud test is permitted. Prove every migrated value
equals its legacy counterpart, then migrate one entry point at a time. Keep
all production defaults unchanged.

### Phase C — test platform provisioning

After explicit human approval, create the test GCP project resources, test
Drive root, least-privilege identity, staging TTL, and audit table. Run only a
manual smoke test against `_test` outputs. This phase requires a separate
approval because it writes cloud resources.

### Phase D — incremental application migration

Migrate POI, Campaign Tracker, Segments, and Automation in separate feature
branches. Each migration must prove offline parity and pass a manual test
environment smoke test before merging to `dev`.

### Phase E — shared-core packaging and test deployment

Package the Cloud Function with its shared core as one explicit deployable
artifact. The current deployment source is only `projects/automation`; no
production deployment workflow changes occur until this packaging work is
reviewed and explicitly approved.

### Phase F — release discipline

Use `feature/<concern>` branches for one concern at a time, merge reviewed
work to `dev`, validate there, then promote a reviewed `dev` release to
`main`. No direct work on `main` and no bulk merge of old feature branches.

Every phase requires offline tests, documentation updates, a security review,
and a rollback note. Cloud writes, deployment, or deletion require explicit
human approval for that exact action.

## Open decisions before Phase C

1. Confirm `<GCP_TEST_PROJECT_ID>`.
2. Identify the producer and schema of `<code>_streach` before enabling OOH
   testing.
3. Confirm the test Drive root and retention period for temporary files and
   staging tables.
4. Confirm the Power BI connection strategy for `_test` marts: a separate test
   workspace/dataset is preferred so production reports cannot discover them.

## Evidence

- `shared/config/settings.py` defines the current shared datasets, tables, and
  country scopes.
- `projects/automation/queries.ini` lists query sources and report query sets.
- `projects/automation/query_orchestrator.py` currently derives output table
  names as `<code>_<query_name>`.
- `projects/segments/scripts/push_to_bq.py` creates the combined segments
  table and temporary CSV-backed tables.
- `projects/automation/upload_backend.py` creates temporary backend-report
  external tables and writes the final backend-report table.
