"""E1: detection on BindBench v2 for the full rule and four independent baselines."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from agentlint.evaluation.baselines import BASELINE_IDS, BASELINE_NAMES, run_baseline
from experiments.revision.common import load_bindbench, prf, write_json


def run() -> dict[str, Any]:
    cases, families = load_bindbench()
    out: dict[str, Any] = {"baselines": {}, "n_workflows": len(cases), "n_families": len(families)}
    for bid in BASELINE_IDS:
        counts: dict[str, dict[str, int]] = defaultdict(
            lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
        )
        flagged_by_variant: dict[str, int] = defaultdict(int)
        missed_by_vuln_kind: dict[str, int] = defaultdict(int)
        fp_by_near_miss: dict[str, int] = defaultdict(int)
        t0 = time.perf_counter()
        for case in cases:
            fam = families[case.family_id]
            predicted = bool(run_baseline(case.workflow, bid))
            positive = case.variant == "vulnerable"
            flagged_by_variant[case.variant] += predicted
            for scope in ("all", fam["origin"]):
                c = counts[scope]
                key = ("tp" if predicted else "fn") if positive else ("fp" if predicted else "tn")
                c[key] += 1
            if positive and not predicted:
                missed_by_vuln_kind[fam["vuln_kind"]] += 1
            if case.variant == "safe_near_miss" and predicted:
                fp_by_near_miss[fam["near_miss"]] += 1
        elapsed = time.perf_counter() - t0
        out["baselines"][bid] = {
            "name": BASELINE_NAMES[bid],
            "counts": dict(counts),
            "metrics": {k: prf(v["tp"], v["fp"], v["fn"]) for k, v in counts.items()},
            "flagged_by_variant": dict(flagged_by_variant),
            "missed_by_vuln_kind": dict(missed_by_vuln_kind),
            "fp_by_near_miss": dict(fp_by_near_miss),
            "runtime_seconds": elapsed,
        }
    write_json("e1_bindbench.json", out)
    return out


if __name__ == "__main__":
    res = run()
    for bid, b in res["baselines"].items():
        m = b["metrics"]["all"]
        print(
            bid,
            b["counts"]["all"],
            {k: round(v, 3) for k, v in m.items()},
            b["flagged_by_variant"],
            "missed",
            b["missed_by_vuln_kind"],
            "nmFP",
            b["fp_by_near_miss"],
        )
