"""
Regression test for IH-035: projects/automation/data_validation.py imports
pandas, but projects/automation/requirements.txt -- the file Cloud
Functions actually installs from (see .github/workflows/deploy.yml's
--source projects/automation) -- did not declare it, a deploy-time
ModuleNotFoundError waiting to happen the moment anything imports
data_validation.py from a reachable path.

This is a static text check of both files; it does not import
data_validation.py (which pulls in google.oauth2 and googleapiclient at
module level) or run anything. No network, no credentials.
"""
from __future__ import annotations

import re


def test_pandas_is_declared_in_automation_requirements(repo_root):
    data_validation_source = (
        repo_root / "projects" / "automation" / "data_validation.py"
    ).read_text(encoding="utf-8")
    assert re.search(r"(?m)^import pandas\b", data_validation_source), (
        "this test assumes data_validation.py still imports pandas; if that "
        "import was removed, this regression guard (and IH-035) may no "
        "longer be relevant and should be revisited"
    )

    requirements = (
        repo_root / "projects" / "automation" / "requirements.txt"
    ).read_text(encoding="utf-8")
    assert re.search(r"(?im)^pandas(==|>=|~=|$)", requirements), (
        "projects/automation/requirements.txt must declare pandas (IH-035): "
        "data_validation.py imports it, and this is the requirements file "
        "Cloud Functions actually installs from"
    )
