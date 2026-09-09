"""Approved production read-only sources, and the reference classifier.

Contract only: additive, imported by no live entry point, enforces
nothing at runtime. Rationale: docs/architecture-and-test-environment-plan.md.

Side-effect free: pure string/pattern logic, no I/O, no client.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Final

from shared.config import settings


class ReferenceCategory(Enum):
    """Every BigQuery reference this repository issues falls in exactly
    one of these. The categories mirror
    docs/architecture-and-test-environment-plan.md's own sections, so the
    classifier and the plan cannot drift apart silently.
    """

    #: Production read-only source (plan "Production read-only sources").
    #: This is the ONLY category the environment gate accepts as a source.
    APPROVED_PRODUCTION_SOURCE = "approved_production_source"

    #: Campaign-control / run-audit metadata (Campaign_Tracker,
    #: Campaign_Runs). Named for the plan's "Test control ... tables"
    #: section. This category identifies the table's ROLE, not which
    #: instance is legitimate: production and _test instances both land
    #: here, and the environment gates -- not this classifier -- decide
    #: which one a given run may touch. Deliberately never accepted as a
    #: source, because Automation *writes* these (status, last_update).
    TEST_CONTROL_TABLE = "test_control_table"

    #: Campaign-scoped output or intermediate the pipeline itself
    #: produces and may re-read (<code>_visitors, <code>_pois,
    #: <code>_Segments, the Back_End_Reports <code> table, ...).
    TEST_OUTPUT_INTERMEDIATE = "test_output_intermediate"

    #: Short-lived staging, typically an external CSV/Drive-backed table
    #: that is created and dropped within one run. Plan lines 156-161:
    #: these are staging resources, NOT published marts, and must not
    #: take the _test published-name suffix.
    TEMPORARY_STAGING = "temporary_staging"

    #: Read by this repository, but no producer for it exists here.
    #: Plan lines 151-153 (<code>_streach). Tracked explicitly rather
    #: than being quietly lumped in with intermediates.
    UNRESOLVED_DEPENDENCY = "unresolved_dependency"


# Country vocabulary, derived from the settings foundation so it cannot
# drift from it. The POI dataset/table pairs are built from
# COUNTRY_POI_TABLES's own (country -> POI_DB_*) mapping rather than from
# two independent alternations, so an invalid cross-country combination
# such as POI_DB_KSA.All_POIs_UAE cannot match. The DB suffixes encode
# the same substitutions get_country_beh() applies (QAT -> QTR,
# EGY -> EGP) -- projects/automation/query_orchestrator.py:83-98.
_COUNTRIES: Final = tuple(sorted(settings.COUNTRY_POI_TABLES))
_POI_PAIRS: Final = tuple(sorted(settings.COUNTRY_POI_TABLES.items()))

_C: Final = "|".join(re.escape(c) for c in _COUNTRIES)
_P: Final = re.escape(settings.PROJECT_ID)

# Every settings-derived value interpolated into a pattern is escaped,
# uniformly. All of them are plain identifiers today, but settings.py
# already carries a dotted constant (DATASET_METADATA_PLACELIFT), so an
# unescaped "." in an approved-source pattern would silently become
# "any character" and widen the allowlist.
_DS_LOCATION_SIGNALS: Final = re.escape(settings.DATASET_LOCATION_SIGNALS)
_DS_AUTOMATED_HWG: Final = re.escape(settings.DATASET_AUTOMATED_HWG)
_DS_FOOTFALL: Final = re.escape(settings.DATASET_FOOTFALL)
_DS_POI_LOOKUPS: Final = re.escape(settings.DATASET_POI_LOOKUPS)
_DS_METADATA: Final = re.escape(settings.DATASET_METADATA)
_DS_BACKEND_REPORTS: Final = re.escape(settings.DATASET_BACKEND_REPORTS)
_DS_CAMPAIGN_SEGMENTS: Final = re.escape(settings.DATASET_CAMPAIGN_SEGMENTS)
_TB_DEVICE_OS: Final = re.escape(settings.TABLE_DEVICE_OS_MAPPING)
_TB_HOME_GRAPH: Final = re.escape(settings.TABLE_HOME_GRAPH)
_TB_WORK_GRAPH: Final = re.escape(settings.TABLE_WORK_GRAPH)
_TB_POL_MAPPING: Final = re.escape(settings.TABLE_HWG_POL_MAPPING)
_TB_BEHAVIOR_LOOKUP: Final = re.escape(settings.TABLE_BEHAVIOR_LOOKUP)
_TB_COUNTRY_LOOKUP: Final = re.escape(settings.TABLE_COUNTRY_LOOKUP)
_TB_CITY_LOOKUP: Final = re.escape(settings.TABLE_CITY_LOOKUP)
_TB_CAMPAIGN_TRACKER: Final = re.escape(settings.TABLE_CAMPAIGN_TRACKER)

#: `code_name` is an INTEGER (docs/modernization-spec.md:110,163;
#: custom_codename.py:95 parses it with type=int; query_orchestrator.py:141
#: stringifies it), so a campaign-scoped name starts with digits only.
#: [0-9] rather than \d: \d is Unicode-aware and would admit Arabic-Indic
#: and other non-ASCII digits, which BigQuery names never contain.
CAMPAIGN_CODE_PATTERN: Final = r"[0-9]+"

#: Query names that become `<code>_<name>` output tables. Taken from the
#: `queries = ` lists in both queries.ini files; "common_queries" is
#: excluded because run_pipeline_queries() recurses and `continue`s on it
#: (query_orchestrator.py:348-363) rather than building a destination.
#: tests/unit/test_source_allowlist_contract.py asserts this set still
#: matches what queries.ini declares.
REPORTING_QUERY_NAMES: Final = frozenset(
    {
        "behavior",
        "device_os",
        "dwell_time",
        "employee_vs_visitor",
        "footfall",
        "footfall_week",
        "home_graph",
        "loyalist_vs_onetime",
        "overlap_ooh",
        "reaction_time",
        "share_of_volume",
        "socioeco",
        "travel_distance",
        "travel_distance_km",
        "visitors",
        "visitors_before",
        "visitors_in_competitors",
    }
)

_QUERY_ALT: Final = "|".join(re.escape(q) for q in sorted(REPORTING_QUERY_NAMES))
_CODE: Final = CAMPAIGN_CODE_PATTERN
_TEST: Final = r"(?:_test)?"
#: GCP project IDs are lowercase ASCII letters, digits and hyphens.
#: [\w-] would be Unicode-aware and match a homoglyph lookalike.
_ANY_PROJECT: Final = r"[a-z0-9][a-z0-9-]*"

_POI_ALL: Final = "|".join(
    rf"{re.escape(db)}\.All_POIs_{re.escape(country)}" for country, db in _POI_PAIRS
)
_POI_BEHAVIOURAL: Final = "|".join(
    rf"{re.escape(db)}\.Behavioral_{re.escape(country)}_RAW_Cumulative"
    for country, db in _POI_PAIRS
)

#: The approved production read-only sources, as anchored patterns.
#: One entry per bullet of the plan's "Production read-only sources".
#: The project part is exactly the production project -- a lookalike in
#: another project is not an approved source.
APPROVED_PRODUCTION_SOURCE_PATTERNS: Final = tuple(
    re.compile(p)
    for p in (
        rf"^{_P}\.{_DS_LOCATION_SIGNALS}\.(?:{_C})_Data$",
        rf"^{_P}\.{_DS_LOCATION_SIGNALS}\.{_TB_DEVICE_OS}$",
        rf"^{_P}\.{_DS_AUTOMATED_HWG}\.{_TB_HOME_GRAPH}$",
        rf"^{_P}\.{_DS_AUTOMATED_HWG}\.{_TB_WORK_GRAPH}$",
        rf"^{_P}\.{_DS_AUTOMATED_HWG}\.{_TB_POL_MAPPING}$",
        rf"^{_P}\.{_DS_FOOTFALL}\.{_TB_BEHAVIOR_LOOKUP}$",
        rf"^{_P}\.{_DS_POI_LOOKUPS}\.(?:lu_date|{_TB_COUNTRY_LOOKUP}|{_TB_CITY_LOOKUP})$",
        rf"^{_P}\.(?:{_POI_ALL})$",
        rf"^{_P}\.(?:{_POI_BEHAVIOURAL})$",
        rf"^{_P}\.Recurring_Segments\.(?:{_C})_HNWI$",
    )
)

#: Campaign-control / audit tables, production and test instances alike.
_CONTROL_TABLE_PATTERN: Final = re.compile(
    rf"^{_ANY_PROJECT}\.{_DS_METADATA}\."
    rf"(?:{_TB_CAMPAIGN_TRACKER}|Campaign_Runs){_TEST}$"
)

#: Staging. The backend-report external table is `<backend_report>_new`
#: (upload_backend.py:289, backend_report is an INTEGER column). The
#: segments external tables are created per uploaded CSV
#: (push_to_bq.create_external_table); their middle section is
#: operator-supplied segment text, so only the campaign-code prefix and
#: the served/controlled final token -- the two parts push_to_bq.py:56-67
#: actually parses -- are constrained here.
_STAGING_PATTERNS: Final = (
    re.compile(rf"^{_ANY_PROJECT}\.{_DS_BACKEND_REPORTS}\.{_CODE}_new$"),
    re.compile(
        rf"^{_ANY_PROJECT}\.{_DS_CAMPAIGN_SEGMENTS}\."
        rf"{_CODE}_[A-Za-z0-9_]+_(?:served|controlled)$"
    ),
)

#: Known-unproduced dependency: <code>_streach (plan lines 151-153).
_UNRESOLVED_PATTERNS: Final = (
    re.compile(
        rf"^{_ANY_PROJECT}\.{_DS_FOOTFALL}\.{_CODE}_streach{_TEST}$"
    ),
)

#: Campaign-scoped outputs/intermediates the pipeline produces itself.
#: Enumerated explicitly -- deliberately NOT "any table in a known output
#: dataset", so a typo or an unexpected new table is reported as
#: unclassified rather than silently absorbed.
_OUTPUT_INTERMEDIATE_PATTERNS: Final = (
    re.compile(
        rf"^{_ANY_PROJECT}\.{_DS_FOOTFALL}\."
        rf"{_CODE}_(?:{_QUERY_ALT}){_TEST}$"
    ),
    re.compile(rf"^{_ANY_PROJECT}\.{_DS_FOOTFALL}\.{_CODE}_pois{_TEST}$"),
    re.compile(
        rf"^{_ANY_PROJECT}\.{_DS_CAMPAIGN_SEGMENTS}\."
        rf"{_CODE}_Segments{_TEST}$"
    ),
    re.compile(
        rf"^{_ANY_PROJECT}\.{_DS_BACKEND_REPORTS}\.{_CODE}{_TEST}$"
    ),
)


def normalise_reference(reference: object) -> str:
    """Strip backticks and surrounding whitespace from a table reference.

    Total: any input is coerced to text so a caller passing a non-string
    gets an unclassified result (and therefore a refusal) rather than an
    AttributeError escaping the gate that was supposed to stop it.
    """
    if reference is None:
        return ""
    if not isinstance(reference, str):
        try:
            reference = str(reference)
        except Exception:  # pragma: no cover - hostile __str__
            return ""
    return reference.replace("`", "").strip()


def classify_reference(reference: str) -> ReferenceCategory | None:
    """Classify one `project.dataset.table` reference.

    Returns None when the reference matches no known category. None means
    "unclassified", which callers must treat as unsafe -- the environment
    gate refuses anything that is not APPROVED_PRODUCTION_SOURCE, so an
    unclassified reference is refused rather than crashing the caller.

    Order matters: the most specific categories are tested before the
    broad campaign-scoped fallbacks, so e.g. `<code>_streach` is reported
    as UNRESOLVED_DEPENDENCY rather than being absorbed into
    TEST_OUTPUT_INTERMEDIATE.
    """
    ref = normalise_reference(reference)

    for pattern in APPROVED_PRODUCTION_SOURCE_PATTERNS:
        if pattern.match(ref):
            return ReferenceCategory.APPROVED_PRODUCTION_SOURCE

    if _CONTROL_TABLE_PATTERN.match(ref):
        return ReferenceCategory.TEST_CONTROL_TABLE

    for pattern in _UNRESOLVED_PATTERNS:
        if pattern.match(ref):
            return ReferenceCategory.UNRESOLVED_DEPENDENCY

    for pattern in _STAGING_PATTERNS:
        if pattern.match(ref):
            return ReferenceCategory.TEMPORARY_STAGING

    for pattern in _OUTPUT_INTERMEDIATE_PATTERNS:
        if pattern.match(ref):
            return ReferenceCategory.TEST_OUTPUT_INTERMEDIATE

    return None


def is_approved_production_source(reference: str) -> bool:
    """True only for references on the approved read-only allowlist."""
    return classify_reference(reference) is ReferenceCategory.APPROVED_PRODUCTION_SOURCE
