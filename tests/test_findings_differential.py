"""Differential test: the bitset analysis equals a brute-force reachability oracle."""

from __future__ import annotations

from collections import deque

import pytest

from agentlint.benchmark.synthetic import TOPOLOGIES, synthetic_workflow
from agentlint.contracts.models import ToolOperation
from agentlint.ir import Workflow, generate_findings
from agentlint.ir.findings import is_discharged


def _oracle(workflow: Workflow) -> set[tuple[str, str, str]]:
    adjacency: dict[str, list[str]] = {n.node_id: [] for n in workflow.nodes}
    for e in workflow.edges:
        adjacency[e.source_id].append(e.target_id)
    out = set()
    for check in workflow.nodes:
        if check.contract is None or check.contract.operation != ToolOperation.CHECK:
            continue
        seen: set[str] = set()
        queue = deque(adjacency[check.node_id])
        while queue:
            cur = queue.popleft()
            if cur in seen:
                continue
            seen.add(cur)
            queue.extend(adjacency[cur])
        for node_id in seen:
            effect = workflow.node(node_id)
            if effect is check or effect.contract is None:
                continue
            if effect.contract.operation != ToolOperation.EFFECT:
                continue
            for r in effect.resources:
                for c in check.resources:
                    if c.key == r.key and not is_discharged(effect, r.key):
                        out.add((check.node_id, effect.node_id, c.resource_id))
    return out


@pytest.mark.parametrize("topology", TOPOLOGIES)
@pytest.mark.parametrize("seed", range(75))
def test_bitset_analysis_matches_bruteforce(topology: str, seed: int) -> None:
    workflow = synthetic_workflow(topology, 40, seed, pool=8, window_resources=False)
    got = {
        (f.check_node_id, f.effect_node_id, f.resource.resource_id)
        for f in generate_findings(workflow)
    }
    assert got == _oracle(workflow)
