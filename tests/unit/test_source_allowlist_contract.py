"""Phase A: approved source-table allowlisting and reference classification.

Contract only -- additive, imported by no live entry point, enforces
nothing at runtime. See docs/architecture-and-test-environment-plan.md.

The centrepiece is TestEveryQueriesIniReferenceIsClassified: it resolves
every table reference both queries.ini files actually issue and asserts
none of them is unclassified. Nothing here contacts BigQuery -- the SQL
text is only ever string-substituted, never executed.
"""
from __future__ import annotations

import configparser
import re

import pytest

from shared.config import settings
from shared.config.source_allowlist import (
    APPROVED_PRODUCTION_SOURCE_PATTERNS,
    CAMPAIGN_CODE_PATTERN,
    REPORTING_QUERY_NAMES,
    ReferenceCategory,
    classify_reference,
    is_approved_production_source,
    normalise_reference,
)
from tests.conftest import import_automation_query_orchestrator


P = settings.PROJECT_ID

# One representative reference per bullet of the plan's
# "Production read-only sources" list (lines 120-129).
PLAN_SOURCE_INVENTORY = (
    f"{P}.{settings.DATASET_LOCATION_SIGNALS}.UAE_Data",
    f"{P}.{settings.DATASET_LOCATION_SIGNALS}.{settings.TABLE_DEVICE_OS_MAPPING}",
    f"{P}.{settings.DATASET_AUTOMATED_HWG}.{settings.TABLE_HOME_GRAPH}",
    f"{P}.{settings.DATASET_AUTOMATED_HWG}.{settings.TABLE_WORK_GRAPH}",
    f"{P}.{settings.DATASET_AUTOMATED_HWG}.{settings.TABLE_HWG_POL_MAPPING}",
    f"{P}.{settings.DATASET_FOOTFALL}.{settings.TABLE_BEHAVIOR_LOOKUP}",
    f"{P}.{settings.DATASET_POI_LOOKUPS}.lu_date",
    f"{P}.{settings.DATASET_POI_LOOKUPS}.{settings.TABLE_COUNTRY_LOOKUP}",
    f"{P}.{settings.DATASET_POI_LOOKUPS}.{settings.TABLE_CITY_LOOKUP}",
    f"{P}.POI_DB_KSA.All_POIs_KSA",
    f"{P}.POI_DB_QTR.Behavioral_QAT_RAW_Cumulative",
    f"{P}.Recurring_Segments.UAE_HNWI",
)

_REFERENCE_RE = re.compile(rf"`?{re.escape(P)}\.[A-Za-z0-9_{{}}]+\.[A-Za-z0-9_{{}}]+`?")


def _resolve_queries_ini(path, replacements, code_placeholder, country, country_beh):
    """Return every table reference the file issues, with placeholders
    resolved exactly the way build_query() resolves them."""
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(path, encoding="utf-8")

    raw = "\n".join(
        value for section in parser.sections() for _, value in parser.items(section)
    )
    for key, replacement in replacements.items():
        raw = raw.replace(key, replacement)
    raw = raw.replace(code_placeholder, "183")
    raw = raw.replace("{country_beh}", country_beh)
    raw = raw.replace("{country}", country)
    raw = raw.replace("{radius}", "50")

    return sorted({normalise_reference(m) for m in _REFERENCE_RE.findall(raw)})


@pytest.fixture
def get_country_beh():
    """The real production mapping (query_orchestrator.py:83-98).

    Function-scoped ON PURPOSE. pytest builds higher-scoped fixtures
    first, so a module-scoped version imported the real automation
    module BEFORE conftest.py's function-scoped _block_real_cloud_clients
    guard was in place. That import is only a by-path load of
    variables.py today, but the guard should cover it, not trail it.
    """
    return import_automation_query_orchestrator().get_country_beh


class TestAllowlistMatchesThePlanInventory:
    @pytest.mark.parametrize("reference", PLAN_SOURCE_INVENTORY)
    def test_each_planned_source_is_approved(self, reference):
        assert is_approved_production_source(reference), reference

    def test_backticks_and_whitespace_are_tolerated(self):
        assert is_approved_production_source(
            f"  `{P}.{settings.DATASET_AUTOMATED_HWG}.{settings.TABLE_HOME_GRAPH}`  "
        )

    def test_an_unknown_table_is_not_approved(self):
        assert not is_approved_production_source(f"{P}.Some_Dataset.some_table")

    def test_a_lookalike_in_another_project_is_not_approved(self):
        assert not is_approved_production_source(
            f"other-project.{settings.DATASET_AUTOMATED_HWG}.{settings.TABLE_HOME_GRAPH}"
        )

    def test_an_unsupported_country_is_not_approved(self):
        assert "ZZZ" not in settings.COUNTRY_POI_TABLES
        assert not is_approved_production_source(
            f"{P}.{settings.DATASET_LOCATION_SIGNALS}.ZZZ_Data"
        )


class TestPatternsAreExactNotBroad:
    """The patterns must reject near-misses, not wave through anything
    that merely lives in a known dataset."""

    def test_cross_country_poi_combinations_do_not_match(self):
        """POI dataset/table pairs are derived from COUNTRY_POI_TABLES,
        so a dataset from one country with a table from another is not
        an approved source even though both halves exist."""
        assert is_approved_production_source(f"{P}.POI_DB_KSA.All_POIs_KSA")
        assert is_approved_production_source(f"{P}.POI_DB_UAE.All_POIs_UAE")
        assert not is_approved_production_source(f"{P}.POI_DB_KSA.All_POIs_UAE")
        assert not is_approved_production_source(f"{P}.POI_DB_UAE.All_POIs_KSA")
        assert not is_approved_production_source(
            f"{P}.POI_DB_KSA.Behavioral_UAE_RAW_Cumulative"
        )

    def test_every_country_pair_from_settings_is_approved(self):
        for country, db in settings.COUNTRY_POI_TABLES.items():
            assert is_approved_production_source(f"{P}.{db}.All_POIs_{country}")
            assert is_approved_production_source(
                f"{P}.{db}.Behavioral_{country}_RAW_Cumulative"
            )

    def test_the_qat_and_egy_db_suffixes_are_the_substituted_ones(self):
        assert settings.COUNTRY_POI_TABLES["QAT"] == "POI_DB_QTR"
        assert settings.COUNTRY_POI_TABLES["EGY"] == "POI_DB_EGP"
        assert not is_approved_production_source(f"{P}.POI_DB_QAT.All_POIs_QAT")

    def test_reporting_query_names_match_what_queries_ini_declares(self, repo_root):
        """If a new query is added to queries.ini, this fails until the
        contract's output-name vocabulary is updated to match."""
        declared = set()
        for name in ("automation", "segments"):
            parser = configparser.ConfigParser(interpolation=None)
            parser.read(repo_root / "projects" / name / "queries.ini", encoding="utf-8")
            for section in parser.sections():
                if parser.has_option(section, "queries"):
                    declared.update(
                        q.strip() for q in parser.get(section, "queries").split(",") if q.strip()
                    )
        # "common_queries" is a recursion directive, not an output table:
        # query_orchestrator.py:348-363 recurses and continues on it.
        assert declared - {"common_queries"} == set(REPORTING_QUERY_NAMES)

    def test_an_unknown_table_in_a_known_output_dataset_is_unclassified(self):
        """The old broad pattern absorbed anything in Back_End_Footfall.
        A typo or an unexpected new table must now surface as None."""
        assert classify_reference(f"{P}.{settings.DATASET_FOOTFALL}.183_vistors") is None
        assert classify_reference(f"{P}.{settings.DATASET_FOOTFALL}.mystery_table") is None
        assert (
            classify_reference(f"{P}.{settings.DATASET_CAMPAIGN_SEGMENTS}.183_Segment")
            is None
        )

    def test_a_non_numeric_campaign_code_is_unclassified(self):
        """code_name is an INTEGER (modernization-spec.md:110,163;
        custom_codename.py:95 parses it with type=int)."""
        assert classify_reference(f"{P}.{settings.DATASET_FOOTFALL}.183_visitors")
        assert classify_reference(f"{P}.{settings.DATASET_FOOTFALL}.abc_visitors") is None
        assert classify_reference(f"{P}.{settings.DATASET_BACKEND_REPORTS}.notacode") is None

    def test_the_campaign_code_pattern_is_ascii_only(self):
        r"""`\d` is Unicode-aware and would admit Arabic-Indic digits,
        which a BigQuery table name never contains."""
        assert CAMPAIGN_CODE_PATTERN == r"[0-9]+"
        assert (
            classify_reference(f"{P}.{settings.DATASET_BACKEND_REPORTS}.١٨٣")
            is None
        )
        assert (
            classify_reference(
                f"{P}.{settings.DATASET_FOOTFALL}.١٨٣_visitors"
            )
            is None
        )

    def test_the_project_pattern_is_ascii_only(self):
        r"""`\w` is Unicode-aware, so a homoglyph project id (Cyrillic
        'a') would otherwise classify as a legitimate test instance."""
        cyrillic = "mаddictdata"  # Cyrillic U+0430, not ASCII 'a'
        assert cyrillic != settings.PROJECT_ID
        assert (
            classify_reference(f"{cyrillic}.{settings.DATASET_FOOTFALL}.183_visitors")
            is None
        )
        assert (
            classify_reference(f"{cyrillic}.{settings.DATASET_METADATA}.Campaign_Tracker")
            is None
        )

    def test_no_approved_source_pattern_contains_an_unescaped_dot(self):
        """The real safety property: inside an approved-source pattern
        every '.' must be a literal separator (\\.) or inside a character
        class -- never a bare wildcard. A dotted settings constant
        interpolated without re.escape() would produce exactly that, and
        would silently widen the allowlist.

        Asserted against the compiled patterns themselves, so deleting a
        re.escape() call fails here. Probing the hand-written separators
        instead would not: those are literal '\\.' in the source and stay
        correct however the interpolated values are treated.
        """
        for pattern in APPROVED_PRODUCTION_SOURCE_PATTERNS:
            text = pattern.pattern
            in_class = False
            index = 0
            while index < len(text):
                char = text[index]
                if char == "\\":
                    index += 2
                    continue
                if char == "[":
                    in_class = True
                elif char == "]":
                    in_class = False
                elif char == "." and not in_class:
                    raise AssertionError(
                        f"unescaped '.' wildcard at offset {index} of approved-source "
                        f"pattern {text!r} -- an interpolated settings value is "
                        f"probably missing re.escape()"
                    )
                index += 1

    def test_every_approved_source_pattern_is_end_anchored(self):
        """classify_reference() matches with .match(), which is a PREFIX
        match. Without a trailing '$' an approved pattern also approves
        every suffixed lookalike -- `<approved>_evil` would classify as
        an APPROVED_PRODUCTION_SOURCE. The escaping guard above does not
        cover this; anchoring is a separate property."""
        for pattern in APPROVED_PRODUCTION_SOURCE_PATTERNS:
            assert pattern.pattern.endswith("$"), (
                f"approved-source pattern {pattern.pattern!r} is not end-anchored; "
                f".match() would approve any suffixed name"
            )

    def test_a_suffixed_lookalike_is_not_an_approved_source(self):
        """The concrete failure the anchor prevents, asserted end to end
        so the guard above cannot be satisfied vacuously."""
        approved = (
            f"{settings.PROJECT_ID}.{settings.DATASET_AUTOMATED_HWG}"
            f".Home_Graph_Cumulative"
        )
        assert classify_reference(approved) is ReferenceCategory.APPROVED_PRODUCTION_SOURCE
        for suffix in ("_evil", "_backup", "2", "_test"):
            assert classify_reference(approved + suffix) is not (
                ReferenceCategory.APPROVED_PRODUCTION_SOURCE
            ), approved + suffix

    def test_a_dotted_settings_value_would_be_neutralised_by_escaping(self):
        """settings.py already carries a dotted constant
        (DATASET_METADATA_PLACELIFT), so this hazard is live, not
        theoretical. Demonstrates the difference escaping makes."""
        dotted = settings.DATASET_METADATA_PLACELIFT
        assert "." in dotted
        assert re.match(re.escape(dotted) + "$", dotted)
        assert not re.match(re.escape(dotted) + "$", dotted.replace(".", "X"))
        # Unescaped, every '.' would match any character:
        assert re.match(dotted + "$", dotted.replace(".", "X"))

    def test_separators_between_components_are_literal_dots(self):
        assert not is_approved_production_source(
            f"{P}X{settings.DATASET_AUTOMATED_HWG}.{settings.TABLE_HOME_GRAPH}"
        )
        assert not is_approved_production_source(
            f"{P}.{settings.DATASET_AUTOMATED_HWG}X{settings.TABLE_HOME_GRAPH}"
        )

    def test_test_instances_of_outputs_are_still_recognised(self):
        assert (
            classify_reference(f"test-proj.{settings.DATASET_FOOTFALL}.183_visitors_test")
            is ReferenceCategory.TEST_OUTPUT_INTERMEDIATE
        )
        assert (
            classify_reference(f"test-proj.{settings.DATASET_BACKEND_REPORTS}.183_test")
            is ReferenceCategory.TEST_OUTPUT_INTERMEDIATE
        )


class TestClassifierCategories:
    def test_control_tables_are_never_approved_sources(self):
        """Automation writes Campaign_Tracker (status, last_update), so it
        must never be classifiable as a read-only source."""
        for name in (
            f"{P}.{settings.DATASET_METADATA}.{settings.TABLE_CAMPAIGN_TRACKER}",
            f"test-project.{settings.DATASET_METADATA}.{settings.TABLE_CAMPAIGN_TRACKER}_test",
            f"test-project.{settings.DATASET_METADATA}.Campaign_Runs_test",
        ):
            assert classify_reference(name) is ReferenceCategory.TEST_CONTROL_TABLE
            assert not is_approved_production_source(name)

    def test_campaign_scoped_outputs_are_intermediates(self):
        for name in (
            f"{P}.{settings.DATASET_FOOTFALL}.183_visitors",
            f"{P}.{settings.DATASET_FOOTFALL}.183_pois",
            f"{P}.{settings.DATASET_CAMPAIGN_SEGMENTS}.183_Segments",
            f"{P}.{settings.DATASET_BACKEND_REPORTS}.183",
        ):
            assert classify_reference(name) is ReferenceCategory.TEST_OUTPUT_INTERMEDIATE

    def test_staging_tables_are_their_own_category(self):
        assert (
            classify_reference(f"{P}.{settings.DATASET_BACKEND_REPORTS}.4471_new")
            is ReferenceCategory.TEMPORARY_STAGING
        )
        assert (
            classify_reference(
                f"{P}.{settings.DATASET_CAMPAIGN_SEGMENTS}.183_UAE_Car_Owners_controlled"
            )
            is ReferenceCategory.TEMPORARY_STAGING
        )

    def test_streach_is_an_unresolved_dependency_not_an_intermediate(self):
        """Plan lines 151-153: read by the OOH query, but this repository
        contains no producer for it."""
        assert (
            classify_reference(f"{P}.{settings.DATASET_FOOTFALL}.183_streach")
            is ReferenceCategory.UNRESOLVED_DEPENDENCY
        )

    def test_an_unknown_reference_is_unclassified_rather_than_guessed(self):
        assert classify_reference("some-project.Mystery.thing") is None

    def test_every_category_is_reachable(self):
        """No category may be decorative -- each must be produced by at
        least one real reference shape."""
        produced = {
            classify_reference(f"{P}.{settings.DATASET_AUTOMATED_HWG}.{settings.TABLE_HOME_GRAPH}"),
            classify_reference(f"{P}.{settings.DATASET_METADATA}.{settings.TABLE_CAMPAIGN_TRACKER}"),
            classify_reference(f"{P}.{settings.DATASET_FOOTFALL}.183_visitors"),
            classify_reference(f"{P}.{settings.DATASET_BACKEND_REPORTS}.4471_new"),
            classify_reference(f"{P}.{settings.DATASET_FOOTFALL}.183_streach"),
        }
        assert produced == set(ReferenceCategory)


class TestEveryQueriesIniReferenceIsClassified:
    """The exhaustive inventory. Every reference either queries.ini
    actually issues must land in exactly one category -- none may be
    unclassified. This is what catches a new table appearing in SQL
    without anyone deciding what it is."""

    def _references(self, repo_root, get_country_beh, component):
        if component == "automation":
            path = repo_root / "projects" / "automation" / "queries.ini"
            replacements = dict(settings.AUTOMATION_QUERY_REPLACEMENTS)
            code_placeholder = "{codename}"
            countries = settings.AUTOMATION_COUNTRY_POI_TABLES
        else:
            path = repo_root / "projects" / "segments" / "queries.ini"
            replacements = dict(settings.SEGMENTS_QUERY_REPLACEMENTS)
            code_placeholder = "{code_name}"
            countries = settings.SEGMENTS_COUNTRY_POI_TABLES

        found = set()
        for country in countries:
            found.update(
                _resolve_queries_ini(
                    path,
                    replacements,
                    code_placeholder,
                    country,
                    get_country_beh(country),
                )
            )
        return sorted(found)

    @pytest.mark.parametrize("component", ["automation", "segments"])
    def test_no_reference_is_unclassified(self, repo_root, get_country_beh, component):
        unclassified = [
            ref
            for ref in self._references(repo_root, get_country_beh, component)
            if classify_reference(ref) is None
        ]
        assert unclassified == [], (
            f"{component}/queries.ini issues references that fall in no "
            f"category. Classify them in shared/config/source_allowlist.py "
            f"rather than widening a pattern to absorb them: {unclassified}"
        )

    @pytest.mark.parametrize("component", ["automation", "segments"])
    def test_every_dataset_and_table_placeholder_is_covered_by_settings(
        self, repo_root, get_country_beh, component
    ):
        """If a reference still contains {...} after substitution, the
        settings placeholder map is missing an entry."""
        leftovers = [
            ref
            for ref in self._references(repo_root, get_country_beh, component)
            if "{" in ref or "}" in ref
        ]
        assert leftovers == [], leftovers

    @pytest.mark.parametrize("component", ["automation", "segments"])
    def test_the_inventory_is_not_trivially_empty(self, repo_root, get_country_beh, component):
        references = self._references(repo_root, get_country_beh, component)
        assert len(references) > 5
        assert any(
            classify_reference(r) is ReferenceCategory.APPROVED_PRODUCTION_SOURCE
            for r in references
        )

    def test_qat_and_egy_country_substitutions_resolve_to_approved_sources(
        self, get_country_beh
    ):
        """QAT -> QTR and EGY -> EGP are the two substitutions that would
        silently produce an unapproved dataset name if dropped."""
        assert get_country_beh("QAT") == "QTR"
        assert get_country_beh("EGY") == "EGP"
        assert is_approved_production_source(
            f"{P}.POI_DB_{get_country_beh('QAT')}.Behavioral_QAT_RAW_Cumulative"
        )
        assert is_approved_production_source(
            f"{P}.POI_DB_{get_country_beh('EGY')}.Behavioral_EGY_RAW_Cumulative"
        )


class TestDocumentedExclusions:
    """Plan lines 163-165: configured-but-unreferenced items stay out of
    the allowlist until a consumer is identified."""

    def test_tbl_cmpgn_test_is_declared_but_referenced_by_no_query(self, repo_root):
        assert "{tbl_cmpgn_test}" in settings.AUTOMATION_QUERY_REPLACEMENTS
        for name in ("automation/queries.ini", "segments/queries.ini"):
            text = (repo_root / "projects" / name).read_text(encoding="utf-8")
            assert "{tbl_cmpgn_test}" not in text

    def test_district_mapping_and_placelift_are_not_approved_sources(self):
        assert not is_approved_production_source(
            f"{P}.{settings.DATASET_DISTRICT_MAPPING}.anything"
        )
        assert not is_approved_production_source(
            f"{P}.{settings.DATASET_METADATA}.{settings.TABLE_PLACELIFT}"
        )

    def test_the_production_table_literally_named_test_is_not_a_source(self):
        assert settings.TABLE_CAMPAIGN_TEST == "test"
        assert not is_approved_production_source(
            f"{P}.{settings.DATASET_METADATA}.{settings.TABLE_CAMPAIGN_TEST}"
        )
