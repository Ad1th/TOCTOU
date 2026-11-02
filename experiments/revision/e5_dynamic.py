"""E5: static analysis versus dynamic schedule testing on the same workflows."""

from __future__ import annotations

import statistics
import time
from typing import Any

from agentlint.dynamic.simulator import random_testing, systematic_testing
from agentlint.evaluation.workflow_io import load_contracts, load_workflow_cases
from agentlint.ir.findings import generate_findings
from experiments.revision.common import ROOT, load_bindbench, write_json

BUDGETS = (1, 2, 5, 10, 20, 50, 100)
PROBS = (0.05, 0.2)


def _corpora() -> dict[str, list[tuple[Any, bool]]]:
    cases, _ = load_bindbench()
    bb = [(c.workflow, c.variant == "vulnerable") for c in cases]
    tools = load_contracts(ROOT / "benchmark/tools/contracts")
    mix = load_workflow_cases(ROOT / "benchmark/benign/benign_workflows.json", tools)
    bn = [(c.workflow, c.variant == "vulnerable") for c in mix]
    return {"bindbench_v2": bb, "benign_mix": bn}


def run() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, items in _corpora().items():
        positives = [w for w, y in items if y]
        negatives = [w for w, y in items if not y]
        t0 = time.perf_counter()
        static_pred = [bool(generate_findings(w)) for w, _ in items]
        static_s = time.perf_counter() - t0

        t0 = time.perf_counter()
        sysv = [systematic_testing(w) for w, _ in items]
        sys_s = time.perf_counter() - t0
        agree = sum(sp == v.detected for sp, v in zip(static_pred, sysv, strict=True))
        sys_exec = [v.executions for v in sysv]
        dyn_fp = sum(v.detected for v, (_, y) in zip(sysv, items, strict=True) if not y)

        curves: dict[str, list[float]] = {}
        rand_cost: dict[str, float] = {}
        for p in PROBS:
            curve = []
            t0 = time.perf_counter()
            for k in BUDGETS:
                hits = sum(
                    random_testing(w, k, p, seed=i).detected for i, w in enumerate(positives)
                )
                curve.append(hits / len(positives))
            rand_cost[str(p)] = time.perf_counter() - t0
            curves[str(p)] = curve
        neg_hits = sum(
            random_testing(w, 100, 0.2, seed=i).detected for i, w in enumerate(negatives)
        )

        out[name] = {
            "n": len(items),
            "n_pos": len(positives),
            "n_neg": len(negatives),
            "static_seconds": static_s,
            "static_recall": sum(sp for sp, (_, y) in zip(static_pred, items, strict=True) if y)
            / len(positives),
            "systematic_seconds": sys_s,
            "systematic_agreement_with_static": agree,
            "systematic_dynamic_false_positives": dyn_fp,
            "systematic_executions_median": statistics.median(sys_exec),
            "systematic_executions_total": sum(sys_exec),
            "systematic_executions_max": max(sys_exec),
            "random_budgets": list(BUDGETS),
            "random_recall_curves": curves,
            "random_negatives_flagged_at_100_p0.2": neg_hits,
            "random_seconds_all_budgets": rand_cost,
        }
    write_json("e5_dynamic.json", out)
    return out


if __name__ == "__main__":
    r = run()
    for k, v in r.items():
        print(k, v)
