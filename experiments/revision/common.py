"""Shared helpers for the revision experiment suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "revision"
FIGURES = ROOT / "paper" / "procedia" / "figures"
GENERATED = ROOT / "paper" / "procedia" / "generated"


def write_json(name: str, payload: Any) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": p, "recall": r, "f1": f}


def load_bindbench() -> tuple[list[Any], dict[str, dict[str, Any]]]:
    from agentlint.evaluation.workflow_io import load_contracts, load_workflow_cases

    base = ROOT / "benchmark" / "bindbench"
    contracts = load_contracts(base / "contracts")
    cases = list(load_workflow_cases(base / "workflows", contracts))
    families = {
        f["family_id"]: f
        for f in json.loads((base / "families.json").read_text(encoding="utf-8"))["families"]
    }
    return cases, families
