"""
Characterization tests for projects/segments/scripts/split_segments.py.

Covers:
  - Deterministic control sampling via a SEEDED random module state,
    injected only from the test process (production code and its call to
    the unseeded, module-level `random` is never modified).
  - IH-007 (Critical, FIXED): Write_output_to_files excludes control-group
    DIDs from served output by comparing each raw file line, stripped, against
    a set of STRIPPED DIDs, so the exclusion check now matches correctly and
    served/control are disjoint.
  - IH-008 (Critical, FIXED): read_data_folder bounds its candidate sample,
    and get_control proportionally reduces the control group for eligible
    pools below 100,000 DIDs instead of requesting more DIDs than exist.

These tests build the exact relative directory layout the module hardcodes
("projects/segments/data/{raw,served,controlled}") under a tmp_path via
the isolated_segments_workspace fixture, and call the REAL functions --
no network, no credentials, no modification to split_segments.py.
"""
from __future__ import annotations

import random

from tests.conftest import import_module_from_path


def _load(repo_root):
    """Load the real split_segments.py the same way projects/segments/
    main.py does: its own directory (scripts/) at the front of sys.path
    for `from variables import *`, and its internal sys.path.append for
    `from input import *` (parent, projects/segments/)."""
    path = repo_root / "projects" / "segments" / "scripts" / "split_segments.py"
    return import_module_from_path("split_segments_under_test", path)


def _write_raw_csv(base, filename: str, dids: list[str]):
    raw_dir = base / "projects" / "segments" / "data" / "raw"
    with open(raw_dir / filename, "w", newline="\n") as f:
        f.write("DID\n")
        for d in dids:
            f.write(d + "\n")


class TestControlSamplingDeterminismUnderAnInjectedSeed:
    """get_control() calls the module-level `random.sample` with no seed
    anywhere in production. To make it reproducible IN TESTS ONLY, these
    tests seed Python's shared `random` module before calling the real,
    unmodified get_control(). pytest/CPython resets nothing globally after
    the test, but this is process-local to the test run and never touches
    split_segments.py or any other production file.
    """

    def test_same_seed_yields_the_same_control_set(self, repo_root, isolated_segments_workspace, monkeypatch):
        mod = _load(repo_root)
        monkeypatch.setattr(mod, "controlled_size", 5, raising=False)
        monkeypatch.setattr(mod, "control_candidate_limit", 50, raising=False)
        population = [f"did-{i:04d}" for i in range(50)]

        random.seed(20260317)
        first = mod.get_control(population)
        random.seed(20260317)
        second = mod.get_control(population)

        assert first == second
        assert len(first) == 5

    def test_different_seeds_can_yield_different_control_sets(self, repo_root, isolated_segments_workspace, monkeypatch):
        mod = _load(repo_root)
        monkeypatch.setattr(mod, "controlled_size", 5, raising=False)
        monkeypatch.setattr(mod, "control_candidate_limit", 50, raising=False)
        population = [f"did-{i:04d}" for i in range(50)]

        random.seed(1)
        a = mod.get_control(population)
        random.seed(2)
        b = mod.get_control(population)

        assert a != b, "extremely unlikely to collide with 5-of-50 sampling under different seeds"


class TestServedControlDisjointness:
    """# FIXED: IH-007 -- served output must NEVER contain a DID that was
    also placed in the control group; that disjointness is the entire
    point of a control group. This test proves it now holds, using the
    real, unmodified Write_output_to_files().
    """

    def test_control_dids_are_excluded_from_served_output(self, repo_root, isolated_segments_workspace):
        mod = _load(repo_root)
        base = isolated_segments_workspace

        dids = [f"did-{i:03d}" for i in range(20)]
        _write_raw_csv(base, "183_UAE_CarOwners_20260317.csv", dids)

        # A control set drawn from (a subset of) the same DIDs, exactly as
        # get_control() would return: a set of STRIPPED strings.
        control = {"did-000", "did-005", "did-010"}
        names = ["183_UAE_CarOwners_20260317"]

        mod.Write_output_to_files(control, names, "UAE")

        served_path = base / "projects" / "segments" / "data" / "served" / "183_UAE_CarOwners_20260317_served.csv"
        served_dids = set(served_path.read_text().splitlines()[1:])  # drop header

        assert not (control & served_dids), (
            "served output must never contain a control-group DID (IH-007)"
        )
        assert served_dids == set(dids) - control

    def test_diagnosis_raw_line_never_equals_a_stripped_set_member(self):
        """Isolates the exact mechanism: `did` from `for did in inpf:` is a
        raw file line (trailing newline included); `control` holds
        stripped strings. `"x\n" in {"x"}` is always False."""
        control = {"did-000"}
        raw_line = "did-000\n"
        assert raw_line not in control
        assert raw_line.strip() in control


class TestControlPoolSubsamplingBelowThreshold:
    """# FIXED: IH-008 -- candidate and control sampling are both bounded,
    and an undersized eligible pool uses the existing 50% control ratio.
    """

    def test_small_segment_file_returns_all_dids_without_crashing(self, repo_root, isolated_segments_workspace):
        mod = _load(repo_root)
        base = isolated_segments_workspace
        # Deliberately far fewer than 100,000 lines -- realistic for a
        # small custom segment.
        dids = [f"did-{i}" for i in range(50)]
        _write_raw_csv(base, "183_UAE_SmallSegment_20260317.csv", dids)
        monkeypatch_excluded = getattr(mod, "excluded_segments", [])
        mod.excluded_segments = []

        try:
            names, for_controlled = mod.read_data_folder("UAE")
        finally:
            mod.excluded_segments = monkeypatch_excluded

        assert set(for_controlled) == set(dids)

    def test_small_pool_uses_proportional_control_size(self, repo_root, isolated_segments_workspace, monkeypatch):
        mod = _load(repo_root)
        population = [f"did-{i}" for i in range(50)]
        monkeypatch.setattr(mod, "controlled_size", 50000, raising=False)

        random.seed(20260820)
        control = mod.get_control(population)

        assert len(control) == 25
        assert control <= set(population)

    def test_empty_pool_returns_empty_control(self, repo_root, isolated_segments_workspace):
        mod = _load(repo_root)

        assert mod.get_control([]) == set()
