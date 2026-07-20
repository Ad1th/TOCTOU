# M0 Foundation Design

## Problem

AgentLint needs a consistent, testable starting point before contracts, frontends, analysis, validation, or benchmark cases are added. Inconsistent tooling and manually produced experiment artifacts would undermine the reproducibility requirements in `FINAL_PROJECT_SPEC.md`.

## Solution

M0 provides a Python 3.12 package, strict quality-tool configuration, structured logging, the specified repository layout, continuous integration, documentation, and a deterministic experiment template. No workflow semantics or security-analysis logic is implemented.

## Interfaces

- `agentlint.configure_json_logger(name, level)`: returns a configured structured logger.
- `experiments.template.runner.write_empty_results(path)`: regenerates an empty CSV result artifact.
- `python -m experiments.template.runner [--results-path PATH]`: command-line template runner.

## Design Decisions

- Standard-library-only runtime code keeps M0 installation simple and deterministic.
- Ruff, Black, mypy, and pytest are development-only dependencies and run in CI.
- The template writes a fixed CSV header with a fixed newline format, allowing byte-for-byte regression tests.
- JSON logs support later experiment automation without introducing a logging dependency.

## Complexity

The template performs constant work and writes one CSV row: `O(1)` time and space excluding filesystem overhead.

## Tests and Acceptance Criteria

- Unit tests cover package metadata, structured log output, and deterministic result generation.
- A layout test checks the required M0 files and directories.
- CI installs the project and runs formatting, linting, type checking, and tests.
- The template command regenerates an empty result artifact from a clean path.

## Threats to Validity

M0 does not validate the future security analysis. It only establishes reproducible engineering conventions. Later milestones must validate their own assumptions, inputs, and outputs.
