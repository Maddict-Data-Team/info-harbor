"""Phase A: published `_test` output-name policy and the staging exemption.

Contract only -- additive, imported by no live entry point, enforces
nothing at runtime. See docs/architecture-and-test-environment-plan.md.

The parity anchors below reproduce today's production names byte for
byte, so this policy layer cannot drift from the live code while nothing
imports it. No test here writes to BigQuery or Drive.
"""
from __future__ import annotations

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


class TestTestSuffixDoesNotCollideWithTheProductionTableNamedTest:
    def test_the_bare_production_name_test_is_not_a_published_test_name(self):
        assert settings.TABLE_CAMPAIGN_TEST == "test"
        assert is_published_test_name(settings.TABLE_CAMPAIGN_TEST) is False

    def test_a_real_suffixed_name_is_recognised(self):
        assert is_published_test_name("Campaign_Tracker_test") is True


class TestThePolicyFailsSafeOnACallerMistake:
    """Each function fails in its own safe direction: resolve must never
    RENAME a production output, and the violation check must never bless
    an unmarked test one. Both must be total -- campaign codenames are
    integers in places, so a non-string name is an ordinary mistake."""

    @pytest.mark.parametrize("environment", ["production", "test", None, object()])
    def test_a_non_environment_value_never_renames_the_output(self, environment):
        """`environment is Environment.PRODUCTION` is an identity check,
        so the string "test" -- which parse_environment() accepts
        elsewhere -- would otherwise fall through and suffix a
        production table."""
        assert (
            resolve_output_name("183_visitors", OutputKind.PUBLISHED, environment)
            == "183_visitors"
        )

    @pytest.mark.parametrize("kind", ["published", None, object()])
    def test_an_unrecognised_output_kind_is_not_assumed_published(self, kind):
        assert (
            resolve_output_name("183_visitors", kind, Environment.TEST) == "183_visitors"
        )

    def test_the_violation_check_fails_the_other_way(self):
        """An unrecognised environment must not cause a rename, but must
        also not silence the check -- so it is treated as a test run."""
        assert published_policy_violation("183_visitors", OutputKind.PUBLISHED, "test")
        assert (
            published_policy_violation(
                "183_visitors", OutputKind.PUBLISHED, Environment.PRODUCTION
            )
            is None
        )

    @pytest.mark.parametrize("name", [183, None, object()])
    @pytest.mark.parametrize("kind", list(OutputKind))
    def test_a_non_string_name_is_handled_not_raised(self, name, kind):
        resolve_output_name(name, kind, Environment.TEST)
        published_policy_violation(name, kind, Environment.TEST)
        is_published_test_name(name)
        would_corrupt_segments_parse(name)

    def test_an_integer_codename_is_suffixed_like_a_string(self):
        assert (
            resolve_output_name(183, OutputKind.PUBLISHED, Environment.TEST) == "183_test"
        )
