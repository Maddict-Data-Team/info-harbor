"""Phase A: published `_test` output-name policy and the staging exemption.

Contract only -- additive, imported by no live entry point, enforces
nothing at runtime. See docs/architecture-and-test-environment-plan.md.

The parity anchors below reproduce today's production names byte for
byte, so this policy layer cannot drift from the live code while nothing
imports it. No test here writes to BigQuery or Drive.
"""
from __future__ import annotations

import re

import pytest

from shared.config import settings
from shared.config.environment import Environment
from shared.config.output_policy import (
    PUBLISHED_TEST_SUFFIX,
    OutputKind,
    backend_report_external_table,
    backend_report_table,
    is_published_test_name,
    published_policy_violation,
    reporting_output_table,
    resolve_output_name,
    segments_combined_table,
    segments_control_token,
    would_corrupt_segments_parse,
    would_flip_served_control_flag,
)


class TestProductionNamesAreByteIdenticalToToday:
    """Each assertion pins one live name-derivation site. If production
    changes shape, this fails rather than silently diverging."""

    def test_reporting_output_matches_query_orchestrator(self, repo_root):
        produced = reporting_output_table(
            settings.PROJECT_ID, settings.DATASET_FOOTFALL, 183, "visitors"
        )
        assert produced == "maddictdata.Back_End_Footfall.183_visitors"

        source = (
            repo_root / "projects" / "automation" / "query_orchestrator.py"
        ).read_text(encoding="utf-8")
        assert (
            'destination = f"{project}.{dataset_footfall}.{codename}_{query_name}"'
            in source
        ), "query_orchestrator.py:380 changed shape; update this contract"

    def test_segments_combined_table_matches_push_to_bq(self, repo_root):
        assert segments_combined_table(183) == "183_Segments"
        source = (
            repo_root / "projects" / "segments" / "scripts" / "push_to_bq.py"
        ).read_text(encoding="utf-8")
        assert 'f"{code_name}_Segments"' in source

    def test_backend_report_table_matches_create_be_table(self, repo_root):
        assert backend_report_table(183) == "183"
        source = (
            repo_root / "projects" / "segments" / "scripts" / "create_be_table.py"
        ).read_text(encoding="utf-8")
        assert 'table(f"{code}")' in source

    def test_backend_report_external_table_matches_upload_backend(self, repo_root):
        assert backend_report_external_table(4471) == "4471_new"
        source = (
            repo_root / "projects" / "automation" / "upload_backend.py"
        ).read_text(encoding="utf-8")
        assert 'table(f"{backend_report}_new")' in source


class TestProductionEnvironmentIsAlwaysTheIdentity:
    """Output parity: this policy must never alter a production name."""

    @pytest.mark.parametrize("kind", list(OutputKind))
    @pytest.mark.parametrize(
        "name",
        [
            "183_visitors",
            "183_Segments",
            "183",
            "4471_new",
            "Campaign_Tracker",
            "already_test",
        ],
    )
    def test_production_names_pass_through_unchanged(self, name, kind):
        assert resolve_output_name(name, kind, Environment.PRODUCTION) == name

    @pytest.mark.parametrize("kind", list(OutputKind))
    def test_production_never_reports_a_violation(self, kind):
        assert published_policy_violation("183_visitors", kind, Environment.PRODUCTION) is None


class TestTestEnvironmentSuffixesPublishedOutputs:
    @pytest.mark.parametrize(
        "base,expected",
        [
            ("183_visitors", "183_visitors_test"),
            ("183_Segments", "183_Segments_test"),
            ("183", "183_test"),
            ("Campaign_Tracker", "Campaign_Tracker_test"),
        ],
    )
    def test_published_outputs_gain_the_suffix(self, base, expected):
        assert resolve_output_name(base, OutputKind.PUBLISHED, Environment.TEST) == expected

    def test_suffixing_is_idempotent(self):
        once = resolve_output_name("183_visitors", OutputKind.PUBLISHED, Environment.TEST)
        twice = resolve_output_name(once, OutputKind.PUBLISHED, Environment.TEST)
        assert once == twice

    def test_a_published_name_without_the_suffix_is_a_violation(self):
        assert published_policy_violation(
            "183_visitors", OutputKind.PUBLISHED, Environment.TEST
        )

    def test_a_correctly_suffixed_published_name_is_clean(self):
        assert (
            published_policy_violation(
                "183_visitors_test", OutputKind.PUBLISHED, Environment.TEST
            )
            is None
        )


class TestStagingIsExemptFromTheSuffix:
    """Plan lines 156-161. The exemption is not a stylistic preference --
    suffixing staging tables silently corrupts segment classification."""

    def test_staging_names_are_not_suffixed_in_a_test_run(self):
        name = "183_UAE_Car_Owners_controlled"
        assert resolve_output_name(name, OutputKind.STAGING, Environment.TEST) == name

    def test_suffixing_staging_is_reported_as_a_violation(self):
        violation = published_policy_violation(
            "183_UAE_Car_Owners_controlled_test", OutputKind.STAGING, Environment.TEST
        )
        assert violation is not None
        assert "staging" in violation

    def test_the_control_token_is_the_final_underscore_token(self, repo_root):
        assert segments_control_token("183_UAE_Car_Owners_controlled") == "controlled"
        assert segments_control_token("183_UAE_Car_Owners_served") == "served"

        source = (
            repo_root / "projects" / "segments" / "scripts" / "push_to_bq.py"
        ).read_text(encoding="utf-8")
        assert "control = table_split[-1]" in source
        assert 'if control == "controlled":' in source

    def test_suffixing_a_controlled_staging_table_would_flip_its_classification(self):
        """The concrete harm: push_to_bq.py:64,67 compares the final
        token to "controlled". Appending _test makes it "test", so the
        row is written as served -- every controlled DID mislabelled."""
        assert would_flip_served_control_flag("183_UAE_Car_Owners_controlled") is True
        assert would_corrupt_segments_parse("183_UAE_Car_Owners_controlled") is True
        assert segments_control_token("183_UAE_Car_Owners_controlled_test") == "test"

    def test_suffixing_a_served_staging_table_does_not_flip_the_boolean(self):
        """Served tables are classified by NOT matching "controlled", so
        the served/control BOOLEAN survives suffixing -- but see the next
        test: the segment LABEL does not."""
        assert would_flip_served_control_flag("183_UAE_Car_Owners_served") is False

    def test_suffixing_also_corrupts_the_segment_label_on_served_tables(self, repo_root):
        """push_to_bq.py:62 derives the segment name from
        `" ".join(table_split[2:-2])`. Appending _test shifts that slice,
        so a served table keeps its correct served/control boolean while
        silently gaining a WRONG segment label. The damage is therefore
        not one-directional: "served output looks fine" is exactly the
        assumption that would let this through."""
        source = (
            repo_root / "projects" / "segments" / "scripts" / "push_to_bq.py"
        ).read_text(encoding="utf-8")
        assert 'Segment = " ".join(table_split[2:-2])' in source

        def segment_label(name: str) -> str:
            return " ".join(name.split("_")[2:-2])

        assert segment_label("183_UAE_Car_Owners_served") == "Car"
        assert segment_label("183_UAE_Car_Owners_served_test") == "Car Owners"
        assert segment_label("183_UAE_Car_Owners_served") != segment_label(
            "183_UAE_Car_Owners_served_test"
        )

    def test_the_exemption_predicate_covers_served_tables_too(self):
        """would_flip_served_control_flag() is False for a served table,
        so a caller that exempts staging on THAT predicate suffixes
        served tables and mislabels their segments. The predicate the
        exemption actually rests on must be True for both."""
        assert would_flip_served_control_flag("183_UAE_Car_Owners_served") is False
        assert would_corrupt_segments_parse("183_UAE_Car_Owners_served") is True
        assert would_corrupt_segments_parse("183_UAE_Car_Owners_controlled") is True

    def test_the_two_predicates_agree_with_the_parser_they_model(self):
        """Pins both against the slices push_to_bq.py actually uses, so
        neither can drift into a tautology."""
        for name in (
            "183_UAE_Car_Owners_served",
            "183_UAE_Car_Owners_controlled",
            "9_KSA_Frequent_Flyers_served",
        ):
            suffixed = name + "_test"
            flag_changed = (
                name.split("_")[-1] == "controlled"
            ) != (suffixed.split("_")[-1] == "controlled")
            label_changed = " ".join(name.split("_")[2:-2]) != " ".join(
                suffixed.split("_")[2:-2]
            )
            assert would_flip_served_control_flag(name) is flag_changed, name
            assert would_corrupt_segments_parse(name) is (
                flag_changed or label_changed
            ), name


class TestTestSuffixDoesNotCollideWithTheProductionTableNamedTest:
    def test_the_bare_production_name_test_is_not_a_published_test_name(self):
        assert settings.TABLE_CAMPAIGN_TEST == "test"
        assert is_published_test_name(settings.TABLE_CAMPAIGN_TEST) is False

    def test_a_real_suffixed_name_is_recognised(self):
        assert is_published_test_name("Campaign_Tracker_test") is True

    def test_the_suffix_constant_is_underscore_prefixed(self):
        assert PUBLISHED_TEST_SUFFIX == "_test"
        assert re.match(r"^_\w+$", PUBLISHED_TEST_SUFFIX)


class TestResolveOutputNameNeverRenamesProduction:
    """Round-4 regression. `environment is Environment.PRODUCTION` is an
    identity check, so the string "test" -- which parse_environment()
    accepts elsewhere, making it an easy thing to pass -- fell straight
    through to the suffixing branch and renamed a PRODUCTION table."""

    @pytest.mark.parametrize("environment", ["production", "test", None, 0, object()])
    def test_a_non_environment_value_leaves_the_name_untouched(self, environment):
        assert (
            resolve_output_name("183_visitors", OutputKind.PUBLISHED, environment)
            == "183_visitors"
        )

    @pytest.mark.parametrize("kind", ["published", None, 0, object()])
    def test_a_non_outputkind_value_leaves_the_name_untouched(self, kind):
        assert (
            resolve_output_name("183_visitors", kind, Environment.TEST)
            == "183_visitors"
        )

    def test_the_real_enum_members_still_behave(self):
        assert (
            resolve_output_name("183_visitors", OutputKind.PUBLISHED, Environment.TEST)
            == "183_visitors_test"
        )
        assert (
            resolve_output_name(
                "183_visitors", OutputKind.PUBLISHED, Environment.PRODUCTION
            )
            == "183_visitors"
        )

    def test_the_violation_check_fails_in_the_other_direction(self):
        """Deliberate asymmetry: an unrecognised environment must not
        cause a rename, but must also not bless an unmarked test name.
        Each function fails in its own safe direction."""
        assert published_policy_violation("183_visitors", OutputKind.PUBLISHED, "test")
        assert published_policy_violation(
            "183_visitors", OutputKind.PUBLISHED, object()
        )
        assert (
            published_policy_violation(
                "183_visitors", OutputKind.PUBLISHED, Environment.PRODUCTION
            )
            is None
        )


class TestNameHandlingIsTotal:
    """environment.py is deliberately total for non-string input; this
    module must match it. Campaign codenames are integers in places
    (source_allowlist.py builds its patterns around an INTEGER campaign
    code), so a caller passing one is an ordinary mistake."""

    @pytest.mark.parametrize("name", [183, None, 4.5, object()])
    def test_a_non_string_name_does_not_raise(self, name):
        resolve_output_name(name, OutputKind.PUBLISHED, Environment.TEST)
        is_published_test_name(name)
        segments_control_token(name)
        would_corrupt_segments_parse(name)

    def test_an_integer_codename_is_suffixed_like_a_string(self):
        assert (
            resolve_output_name(183, OutputKind.PUBLISHED, Environment.TEST)
            == "183_test"
        )

    def test_the_arity_precondition_of_the_exemption_predicate(self):
        """`split[2:-2]` is empty below five tokens, so a degenerate name
        changes nothing measurable. Stated here so a Phase B caller is
        not surprised by it."""
        assert would_corrupt_segments_parse("183_UAE_Car_Owners_served") is True
        assert would_flip_served_control_flag("183_served") is False


class TestTheViolationCheckIsTotalToo:
    """Round-six regression. Every name-consuming function routed
    through _as_name() except this one, and its STAGING branch used the
    name raw -- so the one function whose job is to report a problem
    raised instead."""

    @pytest.mark.parametrize("name", [183, None, 4.5, object()])
    @pytest.mark.parametrize("kind", [OutputKind.STAGING, OutputKind.PUBLISHED])
    def test_a_non_string_name_does_not_raise(self, name, kind):
        published_policy_violation(name, kind, Environment.TEST)

    def test_a_suffixed_staging_name_is_still_reported(self):
        assert published_policy_violation(
            "183_UAE_Car_Owners_served_test", OutputKind.STAGING, Environment.TEST
        )
