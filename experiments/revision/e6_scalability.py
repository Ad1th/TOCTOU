"""E6: scalability on large branching, dense and cyclic workflows (measured, not inferred)."""

from __future__ import annotations

import gc
import statistics
import time
import tracemalloc
from typing import Any

from agentlint.benchmark.synthetic import TOPOLOGIES, synthetic_workflow
from agentlint.ir.findings import generate_findings
from experiments.revision.common import write_json

SIZES = (100, 1_000, 5_000, 10_000, 50_000, 100_000)
V1_SIZES = (100, 250, 500, 1_000)
TRIALS = 3


def _v1_workflow(wf: Any) -> Any:
    from experiments.revision.v1_ir import models as m

    nodes = tuple(
        m.Node(
            n.node_id,
            m.NodeKind(n.kind.value),
            contract=n.contract,
            resources=tuple(
                m.ResourceReference(r.resource_id, r.argument_name) for r in n.resources
            ),
            bindings=tuple(
                m.BindingReference(b.mechanism, b.contract_id, b.authority_enforced)
                for b in n.bindings
            ),
        )
        for n in wf.nodes
    )
    edges = tuple(m.Edge(e.edge_id, e.source_id, e.target_id) for e in wf.edges)
    return m.Workflow(wf.workflow_id, nodes, edges)


def _time(fn: Any, trials: int) -> tuple[float, float]:
    xs = []
    for _ in range(trials):
        gc.collect()
        t0 = time.perf_counter()
        fn()
        xs.append(time.perf_counter() - t0)
    xs.sort()
    return statistics.median(xs), xs[-1]


def run() -> dict[str, Any]:
    rows = []
    for topo in TOPOLOGIES:
        for n in SIZES:
            wf = synthetic_workflow(topo, n, seed=n)
            med, worst = _time(lambda wf=wf: generate_findings(wf), TRIALS)
            tracemalloc.start()
            findings = generate_findings(wf)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            rows.append(
                {
                    "impl": "v2",
                    "topology": topo,
                    "nodes": n,
                    "edges": len(wf.edges),
                    "resources": len({r.key for x in wf.nodes for r in x.resources}),
                    "findings": len(findings),
                    "median_s": med,
                    "max_s": worst,
                    "peak_mib": peak / 2**20,
                }
            )
            print(rows[-1], flush=True)
    from experiments.revision.v1_ir.findings import generate_findings as v1_findings

    for n in V1_SIZES:
        wf = _v1_workflow(synthetic_workflow("layered", n, seed=n))
        v1_count = len(v1_findings(wf))
        med, worst = _time(lambda wf=wf: v1_findings(wf), 1 if n >= 500 else 3)
        wf2 = synthetic_workflow("layered", n, seed=n)
        med2, _ = _time(lambda wf2=wf2: generate_findings(wf2), 3)
        rows.append(
            {
                "impl": "v1",
                "topology": "layered",
                "nodes": n,
                "edges": len(wf.edges),
                "median_s": med,
                "max_s": worst,
                "v2_median_s": med2,
                "v1_findings": v1_count,
                "v2_findings": len(generate_findings(wf2)),
            }
        )
        print(rows[-1], flush=True)
    out = {"trials": TRIALS, "rows": rows}
    write_json("e6_scalability.json", out)
    return out


if __name__ == "__main__":
    run()
