"""E2: false positives on realistic benign workflows and detection of injected risks."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from typing import Any

from agentlint.benchmark.benign import PATTERN_NAMES, PATTERNS, generate_single_pattern, write
from agentlint.benchmark.tool_catalog import write_catalog
from agentlint.evaluation.baselines import BASELINE_IDS, run_baseline
from agentlint.evaluation.workflow_io import _workflow_case, load_contracts, load_workflow_cases
from experiments.revision.common import ROOT, write_json


def run() -> dict[str, Any]:
    tools_dir = ROOT / "benchmark" / "tools"
    benign_dir = ROOT / "benchmark" / "benign"
    write_catalog(tools_dir)
    write(benign_dir)
    contracts = load_contracts(tools_dir / "contracts")
    cases = load_workflow_cases(benign_dir / "benign_workflows.json", contracts)
    meta = {
        w["workflow_id"]: w["meta"]
        for w in json.loads((benign_dir / "benign_workflows.json").read_text())["workflows"]
    }
    benign = [c for c in cases if c.variant == "benign"]
    injected = [c for c in cases if c.variant == "vulnerable"]
    sizes = [len(c.workflow.nodes) for c in cases]
    pattern_counts = Counter(p for c in benign for p in set(meta[c.workflow_id]["patterns"]))
    out: dict[str, Any] = {
        "n_benign": len(benign),
        "n_injected": len(injected),
        "nodes_median": statistics.median(sizes),
        "nodes_max": max(sizes),
        "nodes_min": min(sizes),
        "cyclic_workflows": sum(not c.workflow.is_acyclic() for c in cases),
        "pattern_workflow_counts": {p: pattern_counts[p] for p in PATTERNS},
        "pattern_names": PATTERN_NAMES,
        "baselines": {},
    }
    for bid in BASELINE_IDS:
        fp_workflows = 0
        fp_findings = 0
        fp_by_pattern: dict[str, int] = defaultdict(int)
        for c in benign:
            flagged = run_baseline(c.workflow, bid)
            if flagged:
                fp_workflows += 1
                fp_findings += len(flagged)
                for p in set(meta[c.workflow_id]["patterns"]):
                    fp_by_pattern[p] += 1
        detected = exact = 0
        for c in injected:
            flagged = run_baseline(c.workflow, bid)
            detected += bool(flagged)
            exact += len(flagged) == 1
        out["baselines"][bid] = {
            "benign_fp_workflows": fp_workflows,
            "benign_fp_rate": fp_workflows / len(benign),
            "benign_fp_findings": fp_findings,
            "fp_workflows_containing_pattern": {p: fp_by_pattern[p] for p in PATTERNS},
            "injected_detected": detected,
            "injected_recall": detected / len(injected),
            "injected_exactly_one_finding": exact,
        }
    single: dict[str, dict[str, float]] = {}
    for p in PATTERNS:
        wfs = [_workflow_case(d, contracts).workflow for d in generate_single_pattern(p)]
        single[p] = {
            bid: sum(bool(run_baseline(w, bid)) for w in wfs) / len(wfs) for bid in BASELINE_IDS
        }
    out["single_pattern_fp_rate"] = single
    write_json("e2_benign.json", out)
    return out


if __name__ == "__main__":
    r = run()
    print({k: v for k, v in r.items() if k not in ("baselines", "single_pattern_fp_rate")})
    for p, v in r["single_pattern_fp_rate"].items():
        print(p, v)
    for bid, b in r["baselines"].items():
        print(bid, b)
