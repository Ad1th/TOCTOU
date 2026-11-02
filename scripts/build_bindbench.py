"""Regenerate the BindBench v2 corpus from its declarative specification."""

from __future__ import annotations

from pathlib import Path

from agentlint.benchmark.bindbench import build

if __name__ == "__main__":
    counts = build(Path("benchmark/bindbench"))
    print(counts)
