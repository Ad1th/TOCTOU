"""Regenerate the deterministic empty-results artifact for the experiment template."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Sequence

from agentlint.logging import configure_json_logger

RESULT_HEADERS: tuple[str, ...] = ("experiment_id", "status", "seed", "notes")
DEFAULT_RESULTS_PATH = Path(__file__).with_name("results.csv")
LOGGER = configure_json_logger(__name__)


def write_empty_results(output_path: Path) -> None:
    """Write a deterministic CSV artifact containing the declared result header only."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file, lineterminator="\n")
        writer.writerow(RESULT_HEADERS)


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for the template runner."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-path",
        type=Path,
        default=DEFAULT_RESULTS_PATH,
        help="CSV artifact to regenerate (default: template results.csv).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the template and return a process-compatible status code."""
    arguments = build_parser().parse_args(argv)
    write_empty_results(arguments.results_path)
    LOGGER.info(
        "experiment_results_initialized",
        extra={"results_path": str(arguments.results_path), "row_count": 0},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
