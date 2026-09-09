"""Phase A: log redaction.

Contract only -- additive, imported by no live entry point, enforces
nothing at runtime. See docs/architecture-and-test-environment-plan.md.

Every credential-shaped string in this file is SYNTHETIC. No real key,
token, or device identifier appears here, and no test reads keys/ or
contacts a service.
"""
from __future__ import annotations

import re
import time
from collections import namedtuple
from collections.abc import Mapping

import pytest

from shared.config import settings
from shared.observability.redaction import (
    DEVICE_IDENTIFIER_KEY_NAMES,
    REDACTED,
    SENSITIVE_KEY_NAMES,
    is_sensitive_key,
    redact_mapping,
    redact_text,
)


# --- synthetic fixtures, none of these are real -----------------------
FAKE_PEM = (
    "-----BEGIN PRIVATE KEY-----\n"
    "NOTAREALKEYNOTAREALKEYNOTAREALKEY\n"
    "-----END PRIVATE KEY-----"
)
FAKE_SA_JSON = (
    '{"type": "service_account", "project_id": "maddictdata", '
    '"private_key_id": "abc123fake", '
    f'"private_key": "{FAKE_PEM}", '
    '"client_email": "fake@example.iam.gserviceaccount.com"}'
)
FAKE_OAUTH_JSON = (
    '{"refresh_token": "1//fake-refresh-value", '
    '"access_token": "ya29.fake-access-value", '
    '"client_secret": "GOCSPX-fakesecret"}'
)


class TestRedactsCredentialShapes:
    def test_pem_private_key_block_is_removed(self):
        assert "NOTAREALKEY" not in redact_text(FAKE_PEM)
        assert REDACTED in redact_text(FAKE_PEM)

    def test_service_account_json_loses_its_key_material(self):
        cleaned = redact_text(FAKE_SA_JSON)
        assert "NOTAREALKEY" not in cleaned
        assert "abc123fake" not in cleaned

    def test_service_account_json_keeps_non_secret_context(self):
        """Redaction must not destroy the operational detail that makes a
        log useful."""
        cleaned = redact_text(FAKE_SA_JSON)
        assert "service_account" in cleaned
        assert settings.PROJECT_ID in cleaned

    def test_oauth_tokens_are_removed(self):
        cleaned = redact_text(FAKE_OAUTH_JSON)
        for secret in ("1//fake-refresh-value", "ya29.fake-access-value", "GOCSPX-fakesecret"):
            assert secret not in cleaned

    def test_authorization_header_value_is_removed_whole(self):
        """The entire header value is credential material, scheme
        included; only the header NAME survives, so a reader can still
        tell what was scrubbed."""
        cleaned = redact_text("Authorization: Bearer fake-token-value-12345")
        assert "fake-token-value-12345" not in cleaned
        assert "Bearer" not in cleaned
        assert cleaned == f"Authorization: {REDACTED}"

    def test_a_bare_bearer_token_is_also_removed(self):
        cleaned = redact_text("retrying with Bearer fake-token-value-12345")
        assert "fake-token-value-12345" not in cleaned
        assert "Bearer" in cleaned

    def test_secret_env_var_assignments_are_removed(self):
        cleaned = redact_text(
            "INFO_HARBOR_API_TOKEN=fake-token-abc INFO_HARBOR_FLASK_SECRET_KEY=fake-key-def"
        )
        assert "fake-token-abc" not in cleaned
        assert "fake-key-def" not in cleaned

    def test_legacy_key_file_paths_are_removed(self):
        cleaned = redact_text(
            f"loading credentials from {settings.LEGACY_BIGQUERY_KEY_PATH}"
        )
        assert settings.LEGACY_BIGQUERY_KEY_PATH not in cleaned
        assert REDACTED in cleaned


class TestRedactsDeviceIdentifiers:
    """The backend-report schema carries raw device identifiers --
    projects/automation/data_validation.py:36,37,49."""

    def test_the_key_names_match_the_backend_report_schema(self, repo_root):
        source = (
            repo_root / "projects" / "automation" / "data_validation.py"
        ).read_text(encoding="utf-8")
        for column in ("udid_idfa", "devraw", "dev_ip"):
            assert f'("{column}"' in source
            assert column in DEVICE_IDENTIFIER_KEY_NAMES

    def test_per_device_location_columns_are_redacted_too(self, repo_root):
        """latitude/longitude sit in the same backend-report schema and
        are per-device precise location -- the same class of harm as a
        raw identifier, so the plan's "raw device identifiers" rule
        (plan lines 110-111) covers them."""
        source = (
            repo_root / "projects" / "automation" / "data_validation.py"
        ).read_text(encoding="utf-8")
        for column in ("latitude", "longitude"):
            assert f'("{column}"' in source
            assert column in DEVICE_IDENTIFIER_KEY_NAMES

        cleaned = redact_mapping({"latitude": 25.04653703, "longitude": 55.24033921})
        assert cleaned == {"latitude": REDACTED, "longitude": REDACTED}
        assert "25.04653703" not in redact_text("latitude=25.04653703")

    def test_device_identifier_values_are_removed_from_text(self):
        cleaned = redact_text("udid_idfa=FAKE-UDID-0001 devraw=FAKE-DEVRAW-0002")
        assert "FAKE-UDID-0001" not in cleaned
        assert "FAKE-DEVRAW-0002" not in cleaned

    def test_ip_addresses_are_removed(self):
        cleaned = redact_text("dev_ip 203.0.113.42 seen")
        assert "203.0.113.42" not in cleaned

    def test_did_values_are_removed_from_a_record(self):
        cleaned = redact_mapping({"DID": "FAKE-DID-0003", "campaign_code": 183})
        assert cleaned["DID"] == REDACTED
        assert cleaned["campaign_code"] == 183


class TestRedactsExceptionTextCarryingSql:
    """ui/app.py:219,255,285,360,373 print traceback.format_exc(). An
    upstream Google API error can embed the offending SQL, which may
    carry values."""

    def test_a_bigquery_error_string_loses_embedded_secrets(self):
        message = (
            "google.api_core.exceptions.BadRequest: 400 Syntax error in "
            "query: SELECT DID FROM `maddictdata.Back_End_Footfall.183_visitors` "
            "WHERE udid_idfa='FAKE-UDID-9999' AND token=fake-token-xyz"
        )
        cleaned = redact_text(message)
        assert "FAKE-UDID-9999" not in cleaned
        assert "fake-token-xyz" not in cleaned

    def test_the_useful_part_of_the_error_survives(self):
        message = (
            "google.api_core.exceptions.BadRequest: 400 Syntax error in "
            "query: SELECT DID FROM `maddictdata.Back_End_Footfall.183_visitors`"
        )
        cleaned = redact_text(message)
        assert "BadRequest" in cleaned
        assert "183_visitors" in cleaned


class TestTodaysCodeLogsNoSecretMaterial:
    """Characterization: pin the current, good behaviour so a later
    refactor cannot start logging secrets unnoticed."""

    @pytest.mark.parametrize(
        "relative_path",
        ["projects/automation/main.py", "projects/automation/custom_codename.py"],
    )
    def test_get_secret_result_is_never_printed(self, repo_root, relative_path):
        source = (repo_root / relative_path).read_text(encoding="utf-8")
        assert "def get_secret(" in source
        printed = re.findall(r"print\(([^\n]*)\)", source)
        for call in printed:
            for name in ("secret_data", "secret_data_bq_info", "secret_data_token_info"):
                assert name not in call, f"{relative_path} prints {name}"

    def test_the_ui_never_echoes_the_configured_api_token(self, repo_root):
        source = (repo_root / "ui" / "app.py").read_text(encoding="utf-8")
        printed = re.findall(r"print\(([^\n]*)\)", source)
        for call in printed:
            assert "expected" not in call
            assert "_get_expected_api_token" not in call


class TestTruncatedKeyMaterialIsNotLeaked:
    """A cut log line or clipped exception message contains a BEGIN
    marker with no END. The complete-block rule cannot fire, and a
    generic key=value rule stops at the first space -- which would leave
    the key body in the log verbatim."""

    TRUNCATED = (
        "private_key=-----BEGIN PRIVATE KEY-----\n"
        "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCNOTAREALKEYBODY0001"
    )

    def test_a_truncated_key_body_is_not_left_in_the_output(self):
        cleaned = redact_text(self.TRUNCATED)
        assert "NOTAREALKEYBODY0001" not in cleaned
        assert "MIIEvQIBADANBgkqhkiG9w0BAQEFAASC" not in cleaned
        assert REDACTED in cleaned

    def test_the_begin_marker_itself_is_not_left_dangling(self):
        assert "BEGIN PRIVATE KEY" not in redact_text(self.TRUNCATED)

    @pytest.mark.parametrize(
        "variant",
        [
            "-----BEGIN PRIVATE KEY-----\nNOTAREALKEYBODY0002",
            "-----BEGIN RSA PRIVATE KEY-----\nNOTAREALKEYBODY0003",
            '{"private_key": "-----BEGIN PRIVATE KEY-----\\nNOTAREALKEYBODY0004',
            "error: could not parse -----BEGIN PRIVATE KEY----- NOTAREALKEYBODY0005",
        ],
    )
    def test_every_truncated_shape_is_scrubbed(self, variant):
        cleaned = redact_text(variant)
        assert "NOTAREALKEYBODY" not in cleaned

    def test_a_complete_block_is_still_handled_by_the_tighter_rule(self):
        """The complete-block rule must keep working, and must not eat
        trailing context the way the truncated rule deliberately does."""
        text = f'{{"private_key": "{FAKE_PEM}", "project_id": "maddictdata"}}'
        cleaned = redact_text(text)
        assert "NOTAREALKEY" not in cleaned
        assert "maddictdata" in cleaned

    def test_truncated_redaction_is_idempotent(self):
        once = redact_text(self.TRUNCATED)
        assert redact_text(once) == once


class TestRedactorIsPureAndTotal:
    @pytest.mark.parametrize(
        "raw",
        [
            # bare key=value -- the shape whose value class previously
            # excluded "]", so re-redacting appended a stray bracket
            "token=abc123",
            "password: hunter2",
            "udid_idfa=FAKE-UDID-0009",
            "latitude=25.0465 longitude=55.2403",
            # quoted JSON
            '{"private_key": "secret-value"}',
            '{"refresh_token": "1//fake"}',
            # headers
            "Authorization: Bearer fake-token",
            "retrying with Bearer fake-token",
            # env vars, key paths, IPs
            "INFO_HARBOR_API_TOKEN=fake",
            "loading keys/maddictdata-bq.json",
            "dev_ip 203.0.113.42",
            # already fully redacted
            "token=[REDACTED]",
            "Authorization: [REDACTED]",
        ],
    )
    def test_redaction_is_idempotent_for_every_shape(self, raw):
        once = redact_text(raw)
        twice = redact_text(once)
        thrice = redact_text(twice)
        assert once == twice == thrice, f"not idempotent: {raw!r} -> {once!r} -> {twice!r}"

    def test_repeated_redaction_does_not_grow_the_string(self):
        """The specific regression: token=[REDACTED] -> [REDACTED]] -> ..."""
        text = "token=abc123"
        for _ in range(5):
            text = redact_text(text)
        assert text == f"token={REDACTED}"

    def test_redaction_is_idempotent(self):
        once = redact_text(FAKE_SA_JSON)
        assert redact_text(once) == once

    @pytest.mark.parametrize("value", [None, 0, 1.5, True, b"bytes", [], {}, object()])
    def test_no_input_shape_raises(self, value):
        assert isinstance(redact_text(value), str)

    def test_nested_records_are_redacted_recursively(self):
        record = {
            "run_id": "run-1",
            "credentials": {"private_key": FAKE_PEM},
            "rows": [{"udid_idfa": "FAKE-UDID-0004"}],
        }
        cleaned = redact_mapping(record)
        assert cleaned["run_id"] == "run-1"
        assert cleaned["credentials"]["private_key"] == REDACTED
        assert cleaned["rows"][0]["udid_idfa"] == REDACTED

    def test_non_sensitive_operational_fields_survive_a_record(self):
        """The audit record's useful fields (plan lines 169-174) must not
        be scrubbed."""
        record = {
            "service": "automation",
            "environment": "test",
            "run_id": "run-1",
            "campaign_code": 183,
            "status": "ok",
            "duration_ms": 1234,
        }
        assert redact_mapping(record) == record

    def test_key_name_matching_is_case_insensitive(self):
        assert is_sensitive_key("PRIVATE_KEY")
        assert is_sensitive_key(" Refresh_Token ")
        assert not is_sensitive_key("campaign_code")

    #: Pinned independently of the module's own constants. The loop
    #: below iterates SENSITIVE_KEY_NAMES | DEVICE_IDENTIFIER_KEY_NAMES,
    #: so emptying either constant makes it vacuous and silently drops
    #: all coverage; this list keeps failing.
    KEYS_THAT_MUST_ALWAYS_BE_REDACTED = (
        "access_token",
        "api_key",
        "apikey",
        "authorization",
        "client_secret",
        "cookie",
        "devraw",
        "dev_ip",
        "did",
        "id_token",
        "idfa",
        "latitude",
        "longitude",
        "password",
        "private_key",
        "private_key_id",
        "refresh_token",
        "secret",
        "session",
        "set_cookie",
        "token",
        "udid",
        "udid_idfa",
    )

    @pytest.mark.parametrize("key", KEYS_THAT_MUST_ALWAYS_BE_REDACTED)
    def test_each_pinned_key_is_redacted(self, key):
        assert is_sensitive_key(key)
        assert redact_mapping({key: "FAKE-SENTINEL"})[key] == REDACTED
        assert "FAKE-SENTINEL" not in redact_text(f"{key}=FAKE-SENTINEL")

    def test_the_pinned_list_matches_the_declared_names_exactly(self):
        """Equality, not subset. A subset assertion lets a key be
        DELETED from the module with the whole suite green: the loop
        below just iterates one fewer element, and the pinned list --
        being a subset either way -- still passes."""
        declared = SENSITIVE_KEY_NAMES | DEVICE_IDENTIFIER_KEY_NAMES
        assert set(self.KEYS_THAT_MUST_ALWAYS_BE_REDACTED) == declared

    def test_every_declared_sensitive_key_is_actually_redacted(self):
        for key in sorted(SENSITIVE_KEY_NAMES | DEVICE_IDENTIFIER_KEY_NAMES):
            assert redact_mapping({key: "FAKE-SENTINEL"})[key] == REDACTED
            assert "FAKE-SENTINEL" not in redact_text(f"{key}=FAKE-SENTINEL")


class TestCredentialShapesFoundBySecurityReview:
    """Regressions for leaks the earlier test suite could not reach."""

    @pytest.mark.parametrize(
        "text,secret",
        [
            # requests / google-auth put headers in a dict; its repr uses
            # single quotes, so the Authorization *header* rule cannot
            # match (a quote sits where it expects the ":").
            ("headers={'Authorization': 'Basic FAKEBASICCREDS0001'}", "FAKEBASICCREDS0001"),
            ('{"Authorization": "Bearer FAKEBEARER0002"}', "FAKEBEARER0002"),
            ("{'authorization': 'Bearer FAKEBEARER0003'}", "FAKEBEARER0003"),
        ],
    )
    def test_quoted_authorization_headers_are_redacted(self, text, secret):
        assert secret not in redact_text(text)

    @pytest.mark.parametrize(
        "name",
        [
            "GOOGLE_ACCESS_TOKEN",
            "SLACK_API_KEY",
            "BQ_CLIENT_SECRET",
            "X_AUTH_TOKEN",
            "GCP_SA_PRIVATE_KEY",
            "MY_APP_PASSWORD",
        ],
    )
    def test_prefixed_key_names_are_redacted(self, name):
        r"""`_` is a word character, so a plain \b anchor never matched a
        prefixed variable -- GOOGLE_ACCESS_TOKEN and friends passed
        through untouched."""
        assert "FAKESECRET0004" not in redact_text(f"{name}=FAKESECRET0004")

    @pytest.mark.parametrize(
        "text",
        ["token_count=5", "tokenizer=basic", "did_you_know=yes", "secretariat=1"],
    )
    def test_names_that_merely_contain_a_key_are_not_redacted(self, text):
        """The prefix allowance must not swallow unrelated identifiers."""
        assert redact_text(text) == text

    def test_a_value_starting_with_the_marker_cannot_shield_the_secret(self):
        """Making [REDACTED] an alternative in the value pattern must not
        turn it into a match terminator: everything after it has to be
        consumed too."""
        cleaned = redact_text("token=[REDACTED]FAKESECRET0005")
        assert "FAKESECRET0005" not in cleaned
        assert cleaned == f"token={REDACTED}"

    @pytest.mark.parametrize(
        "text,secret",
        [
            ('{"token": 12345678}', "12345678"),
            ('{"api_key": FAKEUNQUOTED0006}', "FAKEUNQUOTED0006"),
            ('{"password": "ab\\"FAKEESCAPED0007"}', "FAKEESCAPED0007"),
        ],
    )
    def test_unquoted_and_escaped_json_values_are_redacted(self, text, secret):
        """A quoted key with an unquoted value matched neither rule, and
        an embedded escaped quote ended the value match early, leaving a
        fragment of the secret behind."""
        assert secret not in redact_text(text)

    def test_namedtuples_survive_redact_mapping(self):
        """type(record)(cleaned) passes one iterable, but a namedtuple
        needs positional fields -- it raised TypeError, contradicting the
        module's totality guarantee."""
        Point = namedtuple("Point", "x y")
        assert redact_mapping(Point(1, 2)) == Point(1, 2)

        Creds = namedtuple("Creds", "user token")
        assert redact_mapping(Creds("alice", "FAKESECRET0008")).token == REDACTED

    def test_plain_tuples_and_lists_keep_their_type(self):
        assert redact_mapping((1, 2)) == (1, 2)
        assert redact_mapping([1, 2]) == [1, 2]

    @pytest.mark.parametrize(
        "text",
        [
            "headers={'Authorization': 'Basic FAKE0009'}",
            "GOOGLE_ACCESS_TOKEN=FAKE0010",
            "token=[REDACTED]FAKE0011",
            '{"token": 12345678}',
        ],
    )
    def test_every_new_shape_is_also_idempotent(self, text):
        once = redact_text(text)
        assert redact_text(once) == once


class TestPrefixedAndHyphenatedKeyNames:
    """Round-3 regressions. Real logs rarely contain a bare `token=`;
    they contain the WSGI, HTTP-header and env-var spellings of it."""

    @pytest.mark.parametrize(
        "text,secret",
        [
            # WSGI/Flask puts the header in request.environ under this name.
            ("HTTP_AUTHORIZATION=Bearer FAKEWSGI0001", "FAKEWSGI0001"),
            ("HTTP_AUTHORIZATION: Basic FAKEWSGI0002", "FAKEWSGI0002"),
            # Header spellings use "-" where env vars use "_".
            ("X-Api-Key: FAKEHDR0003", "FAKEHDR0003"),
            ("x-auth-token: FAKEHDR0004", "FAKEHDR0004"),
            ("X-API-KEY=FAKEHDR0005", "FAKEHDR0005"),
            ("set-cookie: session=FAKEHDR0006", "FAKEHDR0006"),
            ("Cookie: session=FAKEHDR0007", "FAKEHDR0007"),
            # Arbitrary env prefixes.
            ("BQ_CLIENT_SECRET=FAKEENV0008", "FAKEENV0008"),
            ("SLACK_API_KEY=FAKEENV0009", "FAKEENV0009"),
        ],
    )
    def test_prefixed_and_hyphenated_keys_are_redacted(self, text, secret):
        assert secret not in redact_text(text)

    @pytest.mark.parametrize(
        "text,secret",
        [
            ("HTTP_AUTHORIZATION=Bearer FAKEWSGI0001", "FAKEWSGI0001"),
            ("X-Api-Key: FAKEHDR0003", "FAKEHDR0003"),
            ("set-cookie: session=FAKEHDR0006", "FAKEHDR0006"),
        ],
    )
    def test_those_shapes_are_idempotent(self, text, secret):
        once = redact_text(text)
        assert redact_text(once) == once
        assert secret not in once

    @pytest.mark.parametrize(
        "text",
        [
            # A neighbouring word is not a key: the guards on both sides
            # must hold, or redaction becomes noise and gets switched off.
            "token_count=42",
            "tokenizer=whitespace",
            "did-you-know=yes",
            "secretariat=office",
            "rows_uploaded=1200",
            "latitude_bucket_size=0.5",
        ],
    )
    def test_lookalike_keys_are_left_alone(self, text):
        assert redact_text(text) == text

    def test_the_authorization_scheme_is_redacted_with_its_token(self):
        """The whole header value is credential material. An earlier
        version left `Authorization: [REDACTED] [REDACTED]`, which both
        looked broken and told a reader the scheme."""
        assert redact_text("Authorization: Basic FAKEAUTH0010") == (
            "Authorization: " + REDACTED
        )

    def test_a_truncated_private_key_body_is_redacted(self):
        """A clipped log line has a BEGIN marker and no END, so the
        complete-block rule never fires and the generic rule stops at the
        first space -- leaving the key body verbatim."""
        text = "detail=-----BEGIN PRIVATE KEY-----\nMIIFAKEBODY0011 more body"
        out = redact_text(text)
        assert "MIIFAKEBODY0011" not in out
        assert redact_text(out) == out

    def test_a_truncated_key_does_not_swallow_the_rest_of_a_traceback(self):
        """The rule used to consume to end of input. Applied to traceback
        text -- the stated use -- that deletes every frame after a
        clipped key, destroying exactly the context a responder needs.
        Over-redaction that severe is how a redaction layer gets switched
        off, so the body is consumed and nothing more."""
        text = "\n".join(
            [
                "Traceback (most recent call last):",
                "  detail=-----BEGIN PRIVATE KEY-----",
                "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoFAKEBODY0016",
                '  File "upload_backend.py", line 289, in main',
                "    upload(rows)",
                "ValueError: schema mismatch",
            ]
        )
        out = redact_text(text)
        assert "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoFAKEBODY0016" not in out
        assert 'File "upload_backend.py", line 289, in main' in out
        assert "upload(rows)" in out
        assert "ValueError: schema mismatch" in out
        assert redact_text(out) == out

    def test_two_truncated_keys_in_one_message_are_both_redacted(self):
        text = (
            "first -----BEGIN PRIVATE KEY-----\nAAAAFAKEBODY0017AAAA rows=5 "
            "second -----BEGIN RSA PRIVATE KEY-----\nBBBBFAKEBODY0018BBBB done"
        )
        out = redact_text(text)
        assert "AAAAFAKEBODY0017AAAA" not in out
        assert "BBBBFAKEBODY0018BBBB" not in out
        assert "rows=5" in out and "done" in out


class TestDeviceLocationKeys:
    def test_precise_location_columns_are_redacted_by_key(self):
        """Per-device latitude/longitude is the same class of harm as a
        raw identifier (data_validation.py:36-49)."""
        for key in ("latitude", "longitude"):
            assert is_sensitive_key(key)
            assert redact_mapping({key: 48.8584})[key] == REDACTED
            assert "48.8584" not in redact_text(f"{key}=48.8584")

    def test_a_namedtuple_field_is_redacted_by_NAME_not_position(self):
        """Positional redaction let a `token` field through whenever it
        was not in the position the sequence branch happened to scrub."""
        Row = namedtuple("Row", "campaign token udid rows")
        out = redact_mapping(Row("CMP1", "FAKETUP0012", "FAKETUP0013", 5))
        assert out.campaign == "CMP1"
        assert out.token == REDACTED
        assert out.udid == REDACTED
        assert out.rows == 5

    def test_a_bare_bearer_token_redacts_to_a_stable_string(self):
        """The value bound excludes "]", which is also the last character
        of the marker, so a second pass matched `[REDACTED` and appended
        a stray bracket -- growing the line on every re-redaction."""
        once = redact_text("retrying with Bearer FAKEBEARER0014")
        assert once == "retrying with Bearer " + REDACTED
        assert redact_text(once) == once

    def test_text_trailing_the_marker_is_not_shielded_by_it(self):
        """`Bearer [REDACTED]leaked` must not keep "leaked": a value that
        merely starts with the marker is not already redacted."""
        assert "leaked" not in redact_text("Bearer [REDACTED]leaked")

    def test_a_bearer_token_inside_json_does_not_eat_its_delimiters(self):
        assert redact_text('{"h": "Bearer FAKEBEARER0015"}') == (
            '{"h": "Bearer ' + REDACTED + '"}'
        )


class TestValueShapesWithNoKeyContext:
    """Every other rule needs a `key=` or `"key":` context. The commonest
    logging shape in this repo supplies neither: print(f"... {token}")."""

    @pytest.mark.parametrize(
        "text,secret",
        [
            ("using token ya29.a0AfB_FAKEFAKEFAKE", "ya29.a0AfB_FAKEFAKEFAKE"),
            (
                "key AIzaSyFAKE_BROWSER_KEY_00011122233344455",
                "AIzaSyFAKE_BROWSER_KEY_00011122233344455",
            ),
            ("secret is GOCSPX-FAKESECRETVALUE", "GOCSPX-FAKESECRETVALUE"),
            ("refresh 1//0gFAKEREFRESHTOKENVALUE0001", "1//0gFAKEREFRESHTOKENVALUE0001"),
        ],
    )
    def test_issuer_prefixed_credentials_are_redacted_without_a_key(self, text, secret):
        out = redact_text(text)
        assert secret not in out
        assert redact_text(out) == out

    @pytest.mark.parametrize(
        "text",
        [
            "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrS",
            "table maddictdata.Metadata.Campaign_Tracker rows=1200",
            "campaign 183 country UAE radius 50",
        ],
    )
    def test_ordinary_operational_detail_survives(self, text):
        assert redact_text(text) == text


class TestStructuredValuesUnderASensitiveKey:
    """The unquoted fallback stops at the first space, so a list or a
    nested object under a sensitive key lost only its FIRST element."""

    def test_a_list_value_is_redacted_whole(self):
        out = redact_text('{"token": ["FAKELIST0019", "FAKELIST0020"]}')
        assert "FAKELIST0019" not in out
        assert "FAKELIST0020" not in out

    def test_a_nested_object_value_is_redacted_whole(self):
        out = redact_text('{"secret": {"v": "FAKEOBJ0021", "w": "FAKEOBJ0022"}}')
        assert "FAKEOBJ0021" not in out
        assert "FAKEOBJ0022" not in out

    def test_redact_mapping_remains_the_tool_for_arbitrary_depth(self):
        """The regex handles one level, which is what reaches a log line.
        Structured input has no such limit and must not regress."""
        deep = {"a": {"b": {"c": {"token": "FAKEDEEP0023"}}}}
        assert "FAKEDEEP0023" not in str(redact_mapping(deep))


class TestOverRedactionIsBounded:
    """Redaction that destroys ordinary operational detail gets switched
    off, so the noisy cases are pinned deliberately."""

    @pytest.mark.parametrize(
        "text",
        [
            "binding host=0.0.0.0 port=8080",
            "healthcheck 127.0.0.1 ok",
            "broadcast 255.255.255.255",
        ],
    )
    def test_non_routable_placeholders_are_left_alone(self, text):
        assert redact_text(text) == text

    @pytest.mark.parametrize(
        "text",
        [
            "python 3.11.9 loaded",
            "pandas 1.2.3.4.5 pinned",
            "version 2.1.4.300",
        ],
    )
    def test_version_strings_that_cannot_be_addresses_are_left_alone(self, text):
        assert redact_text(text) == text

    def test_a_real_device_address_is_still_redacted(self):
        assert "203.0.113.45" not in redact_text("dev_ip 203.0.113.45 seen")


class TestTotalityUnderHostileInput:
    """The module docstring promises no input shape raises. Anything that
    reaches a logging call must not turn that call into an outage."""

    def test_a_mapping_whose_items_raises_is_redacted_not_propagated(self):
        class Hostile(Mapping):
            def items(self):
                raise RuntimeError("backing store unavailable")

            def __getitem__(self, key):
                raise KeyError(key)

            def __iter__(self):
                return iter(())

            def __len__(self):
                return 0

        assert redact_mapping(Hostile()) == REDACTED

    def test_a_namedtuple_with_short_fields_redacts_the_unnamed_positions(self):
        """zip() truncates, so a mismatched _fields silently dropped
        trailing values from redaction -- including secret ones."""

        class Broken(tuple):
            _fields = ("campaign",)

        assert redact_mapping(Broken(("CMP1", "FAKESHORT0024"))) == (
            "CMP1",
            REDACTED,
        )

    @pytest.mark.parametrize(
        "value",
        [None, 0, False, 3.5, object(), b"bytes", [], {}, set()],
    )
    def test_no_input_shape_raises(self, value):
        redact_text(value)
        redact_mapping(value)


class TestRedactionIsCheapEnoughForALoggingPath:
    """A redaction helper that can hang is worse than none: it turns a
    logging statement into an outage. These bound the cost rather than
    asserting an output."""

    @pytest.mark.parametrize("length", [100, 1000, 20000])
    def test_a_long_truncated_key_body_is_linear_not_exponential(self, length):
        """The body scanner was written in code to avoid a nested
        quantifier, then the token test reintroduced one:
        `(?:\\[nr]|[A-Za-z0-9+/=]{8,}|...)+` degenerates to
        `(?:[A-Za-z0-9+/=]{8,})+` on a long base64 token that cannot
        reach the anchor. Measured before the fix: 80 characters 0.23s,
        100 characters 14.7s."""
        text = 'could not parse -----BEGIN PRIVATE KEY-----\n' + "A" * length + '",'
        start = time.perf_counter()
        out = redact_text(text)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"{length} chars took {elapsed:.2f}s"
        assert "A" * 32 not in out

    def test_the_key_body_is_redacted_even_when_punctuation_follows_it(self):
        """The body is the leading run of key characters in a token, not
        the whole token: inside a JSON string the token carries the
        closing quote and comma with it."""
        text = '{"private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqFAKE0030\n", "id": 1}'
        out = redact_text(text)
        assert "MIIEvQIBADANBgkqFAKE0030" not in out
        assert '"id": 1' in out

    def test_a_long_ordinary_log_line_is_not_slow(self):
        text = ("campaign 183 country UAE rows 1200 " * 500) + "done"
        start = time.perf_counter()
        redact_text(text)
        assert time.perf_counter() - start < 1.0


class TestKeylessCredentialShapesRoundFive:
    def test_a_bare_jwt_is_redacted(self):
        """`id_token` is already a declared sensitive key; only the
        keyless spelling was missing, and `id_token <jwt>` with a space
        matches no key=value rule."""
        jwt = (
            "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3OCJ9"
            ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJVFAKE0031"
        )
        out = redact_text(f"id_token {jwt}")
        assert jwt not in out
        assert redact_text(out) == out

    @pytest.mark.parametrize(
        "text",
        [
            "eyJ is not a token on its own",
            "maddictdata.Metadata.Campaign_Tracker",
            "version 1.2.3",
        ],
    )
    def test_jwt_lookalikes_are_left_alone(self, text):
        assert redact_text(text) == text


class TestMappingKeysAreDataToo:
    def test_a_device_identifier_used_as_a_key_is_redacted(self):
        """A per-device counter is the shape an audit record naturally
        takes, and redacting only values left the identifier in the log
        verbatim -- while redact_text() of the same string scrubbed it.
        The two entry points must not disagree."""
        assert redact_mapping({"203.0.113.42": 7}) == {REDACTED: 7}

    def test_two_sensitive_keys_do_not_collapse_into_one_entry(self):
        out = redact_mapping({"203.0.113.42": 1, "203.0.113.43": 2})
        assert len(out) == 2
        assert sorted(out.values()) == [1, 2]

    def test_ordinary_keys_are_untouched_and_keep_their_type(self):
        record = {"campaign_code": 183, "rows": 1200, 7: "seven"}
        assert redact_mapping(record) == record


class TestKeyRedactionLosesNoEntries:
    """Round-six regression. The collision guard fired only when the key
    had itself been rewritten, and the suffix it generated was not
    checked -- both drop an entry silently, which is worse than an
    un-redacted log because the record is now wrong as well."""

    def test_an_unredacted_key_equal_to_the_marker_does_not_evict_an_entry(self):
        out = redact_mapping({"10.0.0.1": "first", REDACTED: "second"})
        assert len(out) == 2
        assert sorted(out.values()) == ["first", "second"]

    def test_a_taken_suffix_is_probed_past_not_reused(self):
        out = redact_mapping(
            {"1.1.1.1": "a", "2.2.2.2": "b", f"{REDACTED}_1": "c"}
        )
        assert len(out) == 3
        assert sorted(out.values()) == ["a", "b", "c"]

    def test_ordinary_records_keep_their_keys_exactly(self):
        record = {"campaign_code": 183, "rows": 1200, 7: "seven"}
        assert redact_mapping(record) == record


class TestNonStringKeysAreStillKeys:
    def test_a_bytes_key_is_recognised_as_sensitive(self):
        """str(b"password") is "b'password'", which matches nothing, so
        a bytes key carried its value through untouched."""
        assert is_sensitive_key(b"password")
        assert redact_mapping({b"password": "FAKEBYTES0032"})[b"password"] == REDACTED
        assert redact_mapping({b"udid_idfa": "FAKEBYTES0033"})[b"udid_idfa"] == REDACTED

    def test_a_tuple_key_carrying_an_identifier_is_redacted(self):
        """A (device, date) key carries the identifier as plainly as a
        string key does."""
        out = redact_mapping({("203.0.113.42", "2026-01-01"): 7})
        assert ("203.0.113.42", "2026-01-01") not in out
        assert list(out.values()) == [7]

    def test_an_int_key_keeps_its_type(self):
        assert redact_mapping({7: "seven"}) == {7: "seven"}


class TestKeyRewritingKeepsTheRecordWellFormed:
    """Round-seven regressions on the collision path."""

    def test_a_colliding_bytes_key_stays_bytes(self):
        """The suffix used to be built with an f-string, so the second
        key became the str "b'[REDACTED]'_1" -- a bytes key downgraded
        to a string carrying a bytes repr."""
        out = redact_mapping({b"203.0.113.42": 1, b"203.0.113.43": 2})
        assert all(isinstance(key, bytes) for key in out), out
        assert sorted(out.values()) == [1, 2]

    def test_a_colliding_tuple_key_stays_a_tuple(self):
        out = redact_mapping(
            {("203.0.113.42", "a"): 1, ("203.0.113.43", "a"): 2}
        )
        assert all(isinstance(key, tuple) for key in out), out
        assert sorted(out.values()) == [1, 2]

    def test_an_unhashable_key_is_redacted_not_raised(self):
        """redact_mapping accepts any Mapping, and a Mapping subclass can
        return a key a plain dict never could. The module promises no
        input shape raises -- a logging path that raises is the outage
        the items() guard exists to prevent."""

        class Hostile(Mapping):
            def items(self):
                return [(["dev-1"], 1)]

            def __getitem__(self, key):
                raise KeyError(key)

            def __iter__(self):
                return iter(())

            def __len__(self):
                return 1

        assert redact_mapping(Hostile()) == {REDACTED: REDACTED}
