import importlib.util
import os

from google.cloud import bigquery

# IH-050/IH-051: Cloud Functions deploys ONLY this directory (--source
# projects/automation, .github/workflows/deploy.yml:31) -- shared/ lives
# outside it and is never uploaded. Four successive security reviews
# found problems with sourcing shared/config/settings.py:
#
#   IH-050 (fixed): an unconditional `from shared.config import
#   settings` import-fails outright in the deployed artifact, since
#   shared/ genuinely isn't there.
#
#   IH-051, round 1 (superseded below): inserting a computed repository
#   root into sys.path and then `from shared.config import settings` is
#   a name-based import -- Python resolves it against ANYTHING already
#   on sys.path, not necessarily this repository's own file. Fixed by
#   never mutating sys.path and never importing the generic
#   `shared.config.settings` package name at all -- instead, computing
#   this file's own expected canonical path directly and loading
#   whichever file exists there via importlib.util.spec_from_file_location
#   (never a name-based import).
#
#   IH-051, round 2 (superseded below): round 1 still trusted "two
#   parents above this file" as if it were always this repository's
#   root, purely because *some* file happened to exist at the computed
#   `shared/config/settings.py` path. Fixed by requiring this file's own
#   location to actually match the real repository's shape
#   (`<candidate_root>/projects/automation/variables.py`), verified both
#   syntactically and via `os.path.samefile`.
#
#   IH-051, round 3 (fixed here): round 2's exact-layout + samefile
#   checks are necessary but not sufficient -- they only prove this
#   file sits at the *relative path* `projects/automation/variables.py`
#   below the candidate root, not that the candidate root is genuinely
#   a checkout of this repository at all. A deployed artifact placed at
#   `<ambient_root>/projects/automation/variables.py` (matching that
#   exact expected shape) would satisfy round 2's checks completely
#   while `<ambient_root>` is still not this repository -- a fake
#   `<ambient_root>/shared/config/settings.py` would then be trusted.
#
# Fixed by requiring one more precondition before ever trusting the
# canonical path: `<candidate_root>/.git` must exist (a real checkout
# marker -- either a directory, for a normal clone, or a file, for a
# git worktree, whose content is a `gitdir: <path>` pointer rather than
# a repository itself; `os.path.exists()` is used specifically because
# it accepts either shape, unlike `os.path.isdir()`). This is not proof
# the checkout is genuinely *this* repository, but a real deployment
# artifact (`--source projects/automation`) never carries repository
# metadata for an ambient two-parents-up directory to coincidentally or
# deliberately satisfy, so it closes the gap for the actual threat
# model. Canonical is now trusted only when ALL of: (a) this file's
# location exact-matches the expected repository-relative path, (b)
# that path resolves via `os.path.samefile` to this same running file,
# (c) `<candidate_root>/shared/config/settings.py` exists, AND (d)
# `<candidate_root>/.git` exists. Any failure -> the colocated fallback
# is loaded unconditionally. Never touches sys.path; never performs a
# name-based `import shared...` of any kind; loads either module only
# via importlib.util.spec_from_file_location by exact, explicit path,
# with the spec/loader validated before execution.
#
# tests/unit/test_automation_deploy_artifact_isolated.py proves: the
# full repository layout selects canonical by exact path; the flat
# deployment-artifact layout selects the fallback; a fake
# shared/config/settings.py planted at the exact ambient candidate path
# of a flat artifact still loses to the fallback; a fake settings.py
# planted at the exact NESTED candidate path (matching the full
# projects/automation/variables.py shape, but with no .git marker) also
# still loses to the fallback; canonical and fallback values stay
# equal; and a conflicting fake `shared.config.settings` module/package
# injected into sys.modules/sys.path is never picked up in either
# context.
_this_file = os.path.abspath(__file__)
_script_dir = os.path.dirname(_this_file)
_candidate_root = os.path.dirname(os.path.dirname(_script_dir))
_expected_self_path = os.path.join(_candidate_root, "projects", "automation", "variables.py")
_candidate_canonical_path = os.path.join(_candidate_root, "shared", "config", "settings.py")
_fallback_settings_path = os.path.join(_script_dir, "_shared_config_fallback.py")


def _is_actually_this_file(candidate_path):
    """True only if `candidate_path` is both syntactically this file's
    own expected location AND actually resolves to this same running
    file on disk. Two separate checks, both required: the string check
    alone would trust a coincidental path match without confirming a
    real file is there; samefile() alone (skipped here if the candidate
    doesn't exist) would still need the location to be right in the
    first place."""
    if os.path.normcase(os.path.normpath(candidate_path)) != os.path.normcase(
        os.path.normpath(_this_file)
    ):
        return False
    if not os.path.isfile(candidate_path):
        return False
    try:
        return os.path.samefile(candidate_path, _this_file)
    except OSError:
        return False


def _looks_like_a_real_checkout(candidate_root):
    """True only if `<candidate_root>/.git` exists at all -- neither
    `os.path.isdir()` nor `os.path.isfile()` alone, since a normal clone
    has `.git` as a directory but a git worktree has it as a plain file
    (containing a `gitdir: <path>` pointer, not a repository itself).
    `os.path.exists()` accepts either shape.

    This is the IH-051 round-3 precondition: round 2's exact-layout +
    samefile checks alone (`_is_actually_this_file` above) are
    necessary but NOT sufficient -- a deployed artifact could itself be
    placed at `<ambient_root>/projects/automation/variables.py` (the
    exact expected shape, satisfying round 2's checks completely) while
    `<ambient_root>` is still not a real checkout of this repository.
    Requiring a `.git` marker at the candidate root is not proof the
    checkout is genuinely *this* repository, but a real deployment
    artifact (uploaded via `--source projects/automation`) never
    contains repository metadata for an ambient two-parents-up
    directory to begin with, so this closes the gap for the actual
    threat model without trying to fully authenticate repository
    identity."""
    return os.path.exists(os.path.join(candidate_root, ".git"))


_use_canonical = (
    _is_actually_this_file(_expected_self_path)
    and os.path.isfile(_candidate_canonical_path)
    and _looks_like_a_real_checkout(_candidate_root)
)

if _use_canonical:
    _settings_module_name = "automation_shared_config_settings"
    _settings_path = _candidate_canonical_path
else:
    _settings_module_name = "automation_shared_config_fallback"
    _settings_path = _fallback_settings_path

_settings_spec = importlib.util.spec_from_file_location(_settings_module_name, _settings_path)
if _settings_spec is None or _settings_spec.loader is None:
    raise ImportError(
        f"Could not load a settings module for projects/automation/variables.py "
        f"from {_settings_path!r} (spec_from_file_location returned "
        f"{_settings_spec!r})"
    )
settings = importlib.util.module_from_spec(_settings_spec)
_settings_spec.loader.exec_module(settings)


# credentials

project = settings.PROJECT_ID

# Folders

folder_id_Backend_Reports = settings.DRIVE_BACKEND_REPORTS_FOLDER_ID

# Secret Manager

secret_ber = settings.SECRET_BACKEND_REPORT_TOKEN
secret_bq = settings.SECRET_BIGQUERY_CREDENTIALS

# Keys

key_bq = settings.LEGACY_BIGQUERY_KEY_PATH
key_google_sheets = settings.LEGACY_GOOGLE_SHEETS_KEY_PATH

# BQ Datasets

dataset_LS = settings.DATASET_LOCATION_SIGNALS
dataset_footfall = settings.DATASET_FOOTFALL
dataset_BERs = settings.DATASET_BACKEND_REPORTS
dataset_campaign_segments = settings.DATASET_CAMPAIGN_SEGMENTS
dataset_Districts = settings.DATASET_DISTRICT_MAPPING
dataset_HWG = settings.DATASET_AUTOMATED_HWG
dataset_mt_Placelift = settings.DATASET_METADATA_PLACELIFT
dataset_metadata = settings.DATASET_METADATA

table_HG = settings.TABLE_HOME_GRAPH
tbl_cmpgn_tracker = settings.TABLE_CAMPAIGN_TRACKER
tbl_cmpgn_test = settings.TABLE_CAMPAIGN_TEST
table_behavior_lookup = settings.TABLE_BEHAVIOR_LOOKUP
table_os_mapping = settings.TABLE_DEVICE_OS_MAPPING


# Metadata Status

stage_0 = settings.STATUS_PRE_VALIDATION
stage_1 = settings.STATUS_VALIDATION
stage_2 = settings.STATUS_ACTIVE
stage_3 = settings.STATUS_COMPLETION_PERIOD
stage_4 = settings.STATUS_FINISHED
stage_5 = settings.STATUS_ERROR
stage_6 = settings.STATUS_ON_HOLD

# BQ Schemas

schema_back_end = [
    bigquery.SchemaField("campaign", "STRING"),
    bigquery.SchemaField("LINE", "STRING"),
    bigquery.SchemaField("TIMESTAMP", "TIMESTAMP"),
    bigquery.SchemaField("req_id", "STRING"),
    bigquery.SchemaField("udid_idfa", "STRING"),
    bigquery.SchemaField("devraw", "STRING"),
    bigquery.SchemaField("country", "STRING"),
    bigquery.SchemaField("city", "STRING"),
    bigquery.SchemaField("latitude", "FLOAT64"),
    bigquery.SchemaField("longitude", "FLOAT64"),
    bigquery.SchemaField("dev_os", "STRING"),
    bigquery.SchemaField("dev_language", "STRING"),
    bigquery.SchemaField("dev_make", "STRING"),
    bigquery.SchemaField("dev_type", "STRING"),
    bigquery.SchemaField("connection_type", "STRING"),
    bigquery.SchemaField("carrier", "STRING"),
    bigquery.SchemaField("exchange", "STRING"),
    bigquery.SchemaField("dev_ip", "STRING"),
    bigquery.SchemaField("zip", "STRING"),
    bigquery.SchemaField("creative", "STRING"),
    bigquery.SchemaField("ad_size", "STRING"),
    bigquery.SchemaField("App_ID", "INT64"),
    bigquery.SchemaField("environment", "STRING"),
    bigquery.SchemaField("publisher", "STRING"),
    bigquery.SchemaField("App_Name", "STRING"),
    bigquery.SchemaField("impressions", "INT64"),
    bigquery.SchemaField("clicks", "INT64"),
]


table_mapping = dict(settings.AUTOMATION_COUNTRY_POI_TABLES)


# will transfere to variables later, and change some of the names
static_query_replace = {
    "{hwg_dataset}": dataset_HWG,
    "{footfall_dataset}": dataset_footfall,
    "{project}": project,
    "{metadata_dataset}": dataset_metadata,
    "{campaign_tracker_table}": tbl_cmpgn_tracker,
    "{location_signals_dataset}": dataset_LS,
    "{device_os_mapping_table}": table_os_mapping,
    "{hwg_table}": table_HG,
    "{lookup_behavior_table}": table_behavior_lookup,
    "{back_end_report_dataset}": dataset_BERs,
    "{Campaign_segments_dataset}": dataset_campaign_segments,
    "{tbl_cmpgn_test}": tbl_cmpgn_test,
}

# Campaign Tracker

q_update_status = f"""
UPDATE `maddictdata.Metadata.{tbl_cmpgn_tracker}`
SET status = CASE
    WHEN CURRENT_DATE() BETWEEN start_date + 9 AND end_date + 9 THEN 'Active'
    WHEN CURRENT_DATE() < start_date + 9 THEN 'Validation'
    WHEN CURRENT_DATE() > end_date + 9 THEN 'Completion Period'
    ELSE status
END
WHERE status NOT IN ('Finished', 'On Hold');"""

q_select_active_interval = f"""SELECT
  id,
  campaign_name,
  code_name,
  backend_report,
  status
FROM
  `maddictdata.Metadata.{tbl_cmpgn_tracker}`
WHERE
  ( status = 'Active'
    AND time_interval > 0
    AND DATE_SUB(CURRENT_DATE(), INTERVAL time_interval DAY) >= DATE(last_update) )
  OR status = 'Completion Period';"""


# q_select_by_codename = """SELECT
#   code_name,
#   backend_report
#   FROM
#   `maddictdata.Metadata.{campaign_tracker_table}`
#   where
#   code_name = {codename}
# """


# Main Queries

#########################


def q_deduplicate_ber(code_name):

    return f"""
CREATE OR REPLACE TABLE
  `{project}.{dataset_BERs}.{code_name}` AS
SELECT
  DISTINCT *
FROM
  `{project}.{dataset_BERs}.{code_name}`;
"""
