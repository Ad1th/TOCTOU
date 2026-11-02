"""Rebuild every corpus, run experiments E1-E6 and regenerate all paper assets."""

from __future__ import annotations

from pathlib import Path

from agentlint.benchmark.bindbench import build
from experiments.revision import (
    e1_bindbench,
    e2_benign,
    e3_contract_effort,
    e4_langgraph,
    e5_dynamic,
    e6_scalability,
    make_paper_assets,
)
from experiments.revision.common import ROOT


def main() -> None:
    print("BindBench v2:", build(Path(ROOT / "benchmark" / "bindbench")), flush=True)
    for name, module in (
        ("E1 detection", e1_bindbench),
        ("E2 benign", e2_benign),
        ("E3 contract effort", e3_contract_effort),
        ("E4 LangGraph", e4_langgraph),
        ("E5 dynamic", e5_dynamic),
        ("E6 scalability", e6_scalability),
    ):
        print(f"running {name} ...", flush=True)
        module.run()
    make_paper_assets.main()
    print("assets written to paper/procedia/{figures,generated}", flush=True)


if __name__ == "__main__":
    main()
