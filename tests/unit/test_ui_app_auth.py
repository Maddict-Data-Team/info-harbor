"""
Tests for IH-025's bearer-token auth on ui/app.py's state-changing routes,
and IH-027's fail-closed Flask secret key.

Imports the real ui/app.py via a Flask test client. Every dangerous
underlying operation this file's route bodies reach for (segments/
tracker/automation execution, the live-campaign BigQuery lookup) is
mocked before or during import, so no route exercised here ever
constructs a real Google Cloud client -- the autouse
_block_real_cloud_clients guardrail in tests/conftest.py would fail any
test loudly if one tried. No network, no credentials.
"""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

from tests.conftest import import_module_from_path

VALID_TOKEN = "test-token-correct-horse-battery-staple"

# (endpoint function name, path, http method, mock key whose .assert_called
# this route's authorized-request test should check, optional JSON body
# needed to get past the view's own logic once auth succeeds)
PROTECTED_ROUTES = [
    ("run_campaign_action", "/campaign/143/run/tracker", "POST", "tracker_main", None),
    ("api_run_campaign_action", "/api/campaign/143/run/tracker", "POST", "tracker_main", None),
    ("api_run_all_trackers", "/api/run-all-trackers", "POST", "tracker_main", None),
    ("api_add_campaign", "/api/campaigns/add", "POST", "get_live_campaigns", {"campaign_name": "Test Campaign"}),
    ("run_automation", "/automation", "POST", "automation_main", None),
]

READ_ONLY_ENDPOINTS = {
    "index",
    "documentation",
    "campaign_tracker",
    "campaign_detail",
    "api_campaigns",
    "api_campaign_detail",
    "refresh_campaigns",  # POST verb, but only re-reads campaigns -- see IH-025 doc note
    "health_check",
}


def _fake_module(dotted_name: str, **attrs):
    mod = types.ModuleType(dotted_name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


@pytest.fixture
def app_env(monkeypatch, repo_root):
    """Sets required env vars, injects fakes for every dangerous
    dotted-import-only operation ui/app.py's route bodies reach for, then
    imports ui/app.py fresh. Returns (app_module, mocks_dict)."""
    monkeypatch.setenv("INFO_HARBOR_FLASK_SECRET_KEY", "test-secret-key-not-real")
    monkeypatch.setenv("INFO_HARBOR_API_TOKEN", VALID_TOKEN)

    segments_main_mock = MagicMock(name="segments_main")
    automation_main_mock = MagicMock(name="automation_main")
    tracker_main_mock = MagicMock(name="tracker_main")

    monkeypatch.setitem(
        sys.modules,
        "projects.segments.main_new",
        _fake_module("projects.segments.main_new", main=segments_main_mock),
    )
    monkeypatch.setitem(
        sys.modules,
        "projects.automation.main",
        _fake_module("projects.automation.main", main=automation_main_mock),
    )

    import shared.utils.compatibility as compat

    monkeypatch.setattr(compat, "get_campaign_tracker_main_new", lambda: tracker_main_mock)

    app_path = repo_root / "ui" / "app.py"
    app_module = import_module_from_path("ui_app_under_test", app_path)

    # Empty by default: routes that just iterate .keys() (api_add_campaign)
    # or render campaign attributes (api_campaigns, read-only) both work
    # fine with zero campaigns. api_run_all_trackers is the one route
    # that needs a non-empty dict to actually reach tracker_main inside
    # its per-campaign loop -- its own test overrides return_value.
    live_campaigns_mock = MagicMock(name="get_live_campaigns", return_value={})
    monkeypatch.setattr(app_module, "get_live_campaigns", live_campaigns_mock)

    mocks = {
        "segments_main": segments_main_mock,
        "automation_main": automation_main_mock,
        "tracker_main": tracker_main_mock,
        "get_live_campaigns": live_campaigns_mock,
    }
    return app_module, mocks


@pytest.fixture
def client(app_env):
    app_module, _ = app_env
    app_module.app.testing = True
    return app_module.app.test_client()


class TestFlaskSecretKeyFailsClosed:
    """IH-027."""

    def test_importing_without_the_env_var_refuses_to_start(self, monkeypatch, repo_root):
        monkeypatch.delenv("INFO_HARBOR_FLASK_SECRET_KEY", raising=False)
        monkeypatch.setenv("INFO_HARBOR_API_TOKEN", VALID_TOKEN)

        with pytest.raises(RuntimeError, match="INFO_HARBOR_FLASK_SECRET_KEY"):
            import_module_from_path(
                "ui_app_under_test_no_secret", repo_root / "ui" / "app.py"
            )

    def test_importing_with_an_empty_env_var_also_refuses_to_start(self, monkeypatch, repo_root):
        monkeypatch.setenv("INFO_HARBOR_FLASK_SECRET_KEY", "")
        monkeypatch.setenv("INFO_HARBOR_API_TOKEN", VALID_TOKEN)

        with pytest.raises(RuntimeError, match="INFO_HARBOR_FLASK_SECRET_KEY"):
            import_module_from_path(
                "ui_app_under_test_empty_secret", repo_root / "ui" / "app.py"
            )

    def test_secret_key_does_not_regenerate_between_imports(self, monkeypatch, repo_root):
        """Guards against a random-per-start fallback: two separate
        imports with the SAME env var value must produce the SAME
        secret_key -- if the code ever generated a random key instead of
        reading the env var, this would flake."""
        monkeypatch.setenv("INFO_HARBOR_FLASK_SECRET_KEY", "same-key-both-times")
        monkeypatch.setenv("INFO_HARBOR_API_TOKEN", VALID_TOKEN)

        first = import_module_from_path("ui_app_under_test_key_1", repo_root / "ui" / "app.py")
        second = import_module_from_path("ui_app_under_test_key_2", repo_root / "ui" / "app.py")

        assert first.app.secret_key == "same-key-both-times"
        assert second.app.secret_key == "same-key-both-times"


class TestApiTokenFailsClosedWhenUnconfigured:
    """IH-025: no INFO_HARBOR_API_TOKEN configured must mean every
    protected route rejects everything, never "no auth required"."""

    def test_missing_env_var_rejects_even_a_plausible_looking_token(
        self, monkeypatch, repo_root
    ):
        monkeypatch.setenv("INFO_HARBOR_FLASK_SECRET_KEY", "test-secret-key-not-real")
        monkeypatch.delenv("INFO_HARBOR_API_TOKEN", raising=False)

        tracker_main_mock = MagicMock(name="tracker_main")
        monkeypatch.setitem(
            sys.modules,
            "projects.segments.main_new",
            _fake_module("projects.segments.main_new", main=MagicMock()),
        )
        import shared.utils.compatibility as compat

        monkeypatch.setattr(compat, "get_campaign_tracker_main_new", lambda: tracker_main_mock)

        app_module = import_module_from_path(
            "ui_app_under_test_no_token_configured", repo_root / "ui" / "app.py"
        )
        app_module.app.testing = True
        client = app_module.app.test_client()

        response = client.post(
            "/api/campaign/143/run/tracker",
            headers={"Authorization": "Bearer anything-at-all"},
        )

        assert response.status_code == 401
        tracker_main_mock.assert_not_called()

    def test_empty_env_var_also_fails_closed(self, monkeypatch, repo_root):
        monkeypatch.setenv("INFO_HARBOR_FLASK_SECRET_KEY", "test-secret-key-not-real")
        monkeypatch.setenv("INFO_HARBOR_API_TOKEN", "")

        tracker_main_mock = MagicMock(name="tracker_main")
        monkeypatch.setitem(
            sys.modules,
            "projects.segments.main_new",
            _fake_module("projects.segments.main_new", main=MagicMock()),
        )
        import shared.utils.compatibility as compat

        monkeypatch.setattr(compat, "get_campaign_tracker_main_new", lambda: tracker_main_mock)

        app_module = import_module_from_path(
            "ui_app_under_test_empty_token_configured", repo_root / "ui" / "app.py"
        )
        app_module.app.testing = True
        client = app_module.app.test_client()

        response = client.post(
            "/api/campaign/143/run/tracker",
            headers={"Authorization": "Bearer "},
        )

        assert response.status_code == 401
        tracker_main_mock.assert_not_called()


class TestProtectedRoutesRequireAValidToken:
    @pytest.mark.parametrize("endpoint,path,method,mock_key,json_body", PROTECTED_ROUTES)
    def test_no_token_is_rejected_and_operation_never_runs(
        self, client, app_env, endpoint, path, method, mock_key, json_body
    ):
        _, mocks = app_env
        response = client.open(path, method=method, json=json_body)

        assert response.status_code == 401
        body = response.get_json()
        assert body["success"] is False
        assert VALID_TOKEN not in response.get_data(as_text=True)
        mocks[mock_key].assert_not_called()

    @pytest.mark.parametrize("endpoint,path,method,mock_key,json_body", PROTECTED_ROUTES)
    def test_wrong_token_is_rejected_and_operation_never_runs(
        self, client, app_env, endpoint, path, method, mock_key, json_body
    ):
        _, mocks = app_env
        response = client.open(
            path,
            method=method,
            json=json_body,
            headers={"Authorization": "Bearer wrong-token"},
        )

        assert response.status_code == 401
        mocks[mock_key].assert_not_called()

    @pytest.mark.parametrize("endpoint,path,method,mock_key,json_body", PROTECTED_ROUTES)
    def test_valid_token_is_accepted_and_reaches_the_mocked_operation(
        self, client, app_env, endpoint, path, method, mock_key, json_body
    ):
        _, mocks = app_env
        if endpoint == "api_run_all_trackers":
            # Needs a non-empty campaign dict to actually reach
            # tracker_main inside its per-campaign loop.
            mocks["get_live_campaigns"].return_value = {"143": MagicMock(name="fake_campaign")}
        response = client.open(
            path,
            method=method,
            json=json_body,
            headers={"Authorization": f"Bearer {VALID_TOKEN}"},
        )

        assert response.status_code != 401
        mocks[mock_key].assert_called()


class TestReadOnlyRoutesRemainUnprotected:
    """IH-025 explicitly keeps read-only routes open. /api/refresh is a
    POST verb but only re-reads campaign data (no BigQuery/Drive write,
    no tracker/segments/automation execution) -- classified read-only in
    docs/code-audit.md; this test documents and locks in that choice."""

    def test_health_check_needs_no_token(self, client):
        assert client.get("/health").status_code == 200

    def test_api_campaigns_needs_no_token(self, client):
        assert client.get("/api/campaigns").status_code == 200

    def test_api_refresh_needs_no_token(self, client):
        assert client.post("/api/refresh").status_code == 200


class TestEveryStateChangingRouteIsProtected:
    """Guards against a future POST/PUT/PATCH/DELETE route being added
    without @require_api_token. New routes must be added to either
    PROTECTED_ROUTES (if state-changing) or READ_ONLY_ENDPOINTS (if not)
    in this file, or this test fails -- forcing an explicit choice
    instead of a silent gap."""

    def test_every_write_method_route_is_either_protected_or_explicitly_read_only(
        self, app_env
    ):
        app_module, _ = app_env
        protected_endpoints = {name for name, _, _, _, _ in PROTECTED_ROUTES}
        write_methods = {"POST", "PUT", "PATCH", "DELETE"}

        for rule in app_module.app.url_map.iter_rules():
            if not (rule.methods & write_methods):
                continue
            endpoint = rule.endpoint
            view = app_module.app.view_functions[endpoint]
            is_wrapped = hasattr(view, "__wrapped__")

            if endpoint in protected_endpoints:
                assert is_wrapped, (
                    f"{endpoint} ({rule.rule}) is listed as protected in "
                    f"PROTECTED_ROUTES but its view function is not "
                    f"wrapped with @require_api_token"
                )
            elif endpoint in READ_ONLY_ENDPOINTS:
                assert not is_wrapped, (
                    f"{endpoint} ({rule.rule}) is listed as read-only but "
                    f"its view function IS wrapped -- update "
                    f"READ_ONLY_ENDPOINTS/PROTECTED_ROUTES in this test"
                )
            else:
                pytest.fail(
                    f"New write-method route {endpoint} ({rule.rule}) is not "
                    f"classified in this test as protected or read-only. "
                    f"Classify it in docs/code-audit.md IH-025 and add it "
                    f"to PROTECTED_ROUTES or READ_ONLY_ENDPOINTS here."
                )
