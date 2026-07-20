"""Tests for frozen M0 repository layout requirements."""

from __future__ import annotations

import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DIRECTORIES = (
    "agentlint",
    "papers",
    "benchmark",
    "examples",
    "parser",
    "ir",
    "static",
    "dynamic",
    "experiments",
    "results",
    "plots",
    "docs",
    "artifact",
    "paper",
    "scripts",
    "tests",
)

REQUIRED_FILES = (
    "pyproject.toml",
    "README.md",
    "FINAL_PROJECT_SPEC.md",
    "docs/design/m0-foundation.md",
    "docs/REPRODUCIBILITY.md",
    "experiments/template/config.yaml",
    "experiments/template/README.md",
    "experiments/template/runner.py",
    "experiments/template/results.csv",
    ".github/workflows/ci.yml",
)


def test_required_project_directories_exist() -> None:
    """M0 creates every repository directory required by the project contract."""
    missing_directories = [
        directory for directory in REQUIRED_DIRECTORIES if not (PROJECT_ROOT / directory).is_dir()
    ]

    assert not missing_directories


def test_required_foundation_files_exist() -> None:
    """M0 creates every required foundation file."""
    missing_files = [
        file_name for file_name in REQUIRED_FILES if not (PROJECT_ROOT / file_name).is_file()
    ]

    assert not missing_files


def test_quality_tool_configuration_is_declared() -> None:
    """M0 declares the required formatter, linter, type-checker, and test settings."""
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as configuration_file:
        configuration = tomllib.load(configuration_file)

    tool_configuration = configuration["tool"]

    assert tool_configuration["black"]["target-version"] == ["py312"]
    assert "ruff" in tool_configuration
    assert tool_configuration["mypy"]["strict"] is True
    assert tool_configuration["pytest"]["ini_options"]["testpaths"] == ["tests"]
