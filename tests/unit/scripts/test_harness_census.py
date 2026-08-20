"""The ratchet that notices a disappearing test.

"It overwrote a test, it deleted a test, it declared everything done" — the cheapest way to turn
a red gate green is to remove what is red. This is the sensor for that, so it needs its own.
"""

from __future__ import annotations

import test_census


def _write(directory, name: str, body: str):
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_counts_test_functions_across_nested_directories(tmp_path):
    _write(tmp_path, "test_a.py", "def test_one():\n    pass\n\ndef test_two():\n    pass\n")
    _write(tmp_path / "unit", "test_b.py", "async def test_three():\n    pass\n")
    assert test_census.count_tests(tmp_path) == (3, 2)


def test_helpers_and_fixtures_are_not_counted_as_tests(tmp_path):
    _write(
        tmp_path,
        "test_a.py",
        "def make_thing():\n    pass\n\n"
        "def testing_helper():\n    pass\n\n"
        "def test_real():\n    pass\n",
    )
    assert test_census.count_tests(tmp_path)[0] == 1


def test_files_not_named_test_are_ignored(tmp_path):
    _write(tmp_path, "conftest.py", "def test_not_collected():\n    pass\n")
    _write(tmp_path, "test_a.py", "def test_real():\n    pass\n")
    assert test_census.count_tests(tmp_path) == (1, 1)


def test_a_drop_is_reported_and_a_rise_is_not(tmp_path, monkeypatch):
    baseline = tmp_path / "test-census.json"
    monkeypatch.setattr(test_census, "BASELINE", baseline)

    tests_dir = tmp_path / "tests"
    _write(tests_dir, "test_a.py", "def test_one():\n    pass\n\ndef test_two():\n    pass\n")
    monkeypatch.setattr(test_census, "repo_root", lambda: tmp_path)

    assert test_census.main([]) == 0  # first run records the baseline
    assert test_census.read_baseline() == 2

    _write(tests_dir, "test_a.py", "def test_one():\n    pass\n")
    assert test_census.main([]) == 1, "a lost test must be reported"

    _write(tests_dir, "test_a.py", "def test_one():\n    pass\n\ndef test_two():\n    pass\n")
    assert test_census.main([]) == 0
