"""
Regression test for IH-049: both requirements.txt files pin
pandas==2.1.1 but did not pin numpy, so `pip install` was free to resolve
the latest numpy (2.x), which is ABI-incompatible with pandas 2.1.1 and
fails at `import pandas` time.

This is a static text check of both files; it does not install anything
or import pandas/numpy. No network, no credentials.
"""
from __future__ import annotations

import re

PANDAS_PIN = "pandas==2.1.1"
EXPECTED_NUMPY_PIN = "numpy==1.26.4"


def _assert_pandas_pin_unchanged(requirements: str, label: str) -> None:
    assert PANDAS_PIN in requirements, (
        f"this test assumes {label} still pins {PANDAS_PIN}; if that pin "
        "changed, the numpy compatibility constraint below should be "
        "revisited"
    )


def _assert_numpy_constrained(requirements: str, label: str) -> None:
    match = re.search(r"(?im)^numpy==([0-9][^\s]*)\s*$", requirements)
    assert match is not None, (
        f"{label} must pin numpy to a version compatible with {PANDAS_PIN} "
        "(IH-049): pandas==2.1.1 is not compatible with numpy>=2, and an "
        "unpinned numpy resolves to the latest 2.x release"
    )
    assert match.group(1) == "1.26.4", (
        f"{label} pins numpy=={match.group(1)}, but the version validated "
        f"against {PANDAS_PIN} (IH-049) is {EXPECTED_NUMPY_PIN}"
    )


def test_root_requirements_pin_numpy_compatible_with_pandas(repo_root):
    requirements = (repo_root / "requirements.txt").read_text(encoding="utf-8")
    _assert_pandas_pin_unchanged(requirements, "requirements.txt")
    _assert_numpy_constrained(requirements, "requirements.txt")


def test_automation_requirements_pin_numpy_compatible_with_pandas(repo_root):
    requirements = (
        repo_root / "projects" / "automation" / "requirements.txt"
    ).read_text(encoding="utf-8")
    _assert_pandas_pin_unchanged(
        requirements, "projects/automation/requirements.txt"
    )
    _assert_numpy_constrained(
        requirements, "projects/automation/requirements.txt"
    )
