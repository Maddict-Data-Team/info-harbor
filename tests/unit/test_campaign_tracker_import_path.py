"""
Regression test for IH-014: `from projects.campaign_tracker.main_new
import main` can never resolve -- the real directory is
projects/campaign-tracker (hyphen), which is not a valid Python
package-name character, independent of any __init__.py files.

get_campaign_tracker_main_new() (shared/utils/compatibility.py) loads
main_new.py directly from its file path via importlib instead. This test
loads it and confirms `main` is callable -- it does NOT call main() itself,
since that constructs a real BigQuery client (main_new.py's
create_client()); the autouse _block_real_cloud_clients fixture in
tests/conftest.py would catch that if it happened, but this test avoids it
entirely by design. No network, no credentials.
"""
from __future__ import annotations


def test_get_campaign_tracker_main_new_returns_a_callable(repo_root, monkeypatch):
    monkeypatch.syspath_prepend(str(repo_root))
    from shared.utils.compatibility import get_campaign_tracker_main_new

    tracker_main = get_campaign_tracker_main_new()

    assert callable(tracker_main)
    assert tracker_main.__name__ == "main"


def test_broken_dotted_import_path_still_cannot_resolve(repo_root, monkeypatch):
    """Documents why the fix is necessary: confirms the ModuleNotFoundError
    IH-014 describes is real, so a future reader isn't tempted to "simplify"
    get_campaign_tracker_main_new() back into a normal import statement."""
    import pytest

    monkeypatch.syspath_prepend(str(repo_root))
    with pytest.raises(ModuleNotFoundError):
        import projects.campaign_tracker.main_new  # noqa: F401
