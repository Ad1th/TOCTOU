"""Tests for the deterministic experiment template."""

from __future__ import annotations

from pathlib import Path

from experiments.template.runner import RESULT_HEADERS, main, write_empty_results


def test_write_empty_results_is_deterministic(tmp_path: Path) -> None:
    """The runner creates the same header-only artifact on repeated writes."""
    results_path = tmp_path / "nested" / "results.csv"

    write_empty_results(results_path)
    first_contents = results_path.read_text(encoding="utf-8")
    write_empty_results(results_path)
    second_contents = results_path.read_text(encoding="utf-8")

    assert first_contents == second_contents
    assert first_contents == ",".join(RESULT_HEADERS) + "\n"


def test_main_accepts_custom_results_path(tmp_path: Path) -> None:
    """The command-line entry point writes a custom deterministic output path."""
    results_path = tmp_path / "custom.csv"

    exit_code = main(["--results-path", str(results_path)])

    assert exit_code == 0
    assert results_path.read_text(encoding="utf-8") == ",".join(RESULT_HEADERS) + "\n"
