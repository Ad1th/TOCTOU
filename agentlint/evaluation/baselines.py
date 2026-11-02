"""Independently implemented baseline detectors.

None of these baselines import or call AgentLint's propagation or finding code
(``agentlint.ir.dependencies`` / ``agentlint.ir.findings``). They read only the IR data
structures and use their own graph traversal, so their results are not derived from the
system under test. Each baseline adds one ingredient of the full rule:

* ``B1`` ordered pair      -- any check-operation node listed before any effect-operation
  node, ignoring edges, resources and bindings (a lexical "check then act" pattern match).
* ``B2`` reachability      -- the effect is reachable from the check along graph edges and
  both declare the same resource key; bindings are ignored.
* ``B3`` binding presence  -- B2, suppressed when the effect node carries any binding whose
  mechanism is not ``none`` (no authority or scope reasoning).
* ``B3A`` authority-aware  -- B3, but a binding only counts if the effect's contract marks
  the authority as enforcing it; binding scope is still ignored.
* ``B4`` AgentLint          -- the full rule in :mod:`agentlint.ir.findings`.

Each baseline returns the set of (check node, effect node, resource key) triples it flags.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from typing import Literal

from agentlint.contracts.models import AuthorityBehavior, BindingMechanism, ToolOperation
from agentlint.ir.models import Node, Workflow

BaselineId = Literal["B1", "B2", "B3", "B3A", "B4"]
BASELINE_IDS: tuple[BaselineId, ...] = ("B1", "B2", "B3", "B3A", "B4")
BASELINE_NAMES: dict[str, str] = {
    "B1": "Ordered check-effect pair",
    "B2": "+ reachability and resource match",
    "B3": "+ binding presence",
    "B3A": "+ authority awareness",
    "B4": "AgentLint (+ effect-local, resource-scoped)",
}

Triple = tuple[str, str, str]


def run_baseline(workflow: Workflow, baseline_id: BaselineId) -> frozenset[Triple]:
    """Return the (check, effect, resource) triples flagged by ``baseline_id``."""

    if baseline_id == "B4":
        from agentlint.ir.findings import generate_findings

        return frozenset(
            (f.check_node_id, f.effect_node_id, f.resource.key) for f in generate_findings(workflow)
        )
    return _BASELINES[baseline_id](workflow)


def _op(node: Node) -> ToolOperation | None:
    return node.contract.operation if node.contract is not None else None


def _b1(workflow: Workflow) -> frozenset[Triple]:
    flagged: set[Triple] = set()
    seen_checks: list[Node] = []
    for node in workflow.nodes:
        if _op(node) == ToolOperation.CHECK:
            seen_checks.append(node)
        elif _op(node) == ToolOperation.EFFECT:
            for check in seen_checks:
                flagged.add((check.node_id, node.node_id, "*"))
    return frozenset(flagged)


def _reachable_from(workflow: Workflow, start: str) -> set[str]:
    adjacency: dict[str, list[str]] = {n.node_id: [] for n in workflow.nodes}
    for edge in workflow.edges:
        adjacency[edge.source_id].append(edge.target_id)
    seen: set[str] = set()
    queue = deque(adjacency[start])
    while queue:
        current = queue.popleft()
        if current in seen:
            continue
        seen.add(current)
        queue.extend(adjacency[current])
    return seen


def _reachable_pairs(workflow: Workflow) -> list[tuple[Node, Node, str]]:
    by_id = {n.node_id: n for n in workflow.nodes}
    pairs: list[tuple[Node, Node, str]] = []
    for check in workflow.nodes:
        if _op(check) != ToolOperation.CHECK:
            continue
        check_keys = {r.identity or r.resource_id for r in check.resources}
        for target_id in sorted(_reachable_from(workflow, check.node_id)):
            effect = by_id[target_id]
            if effect is check or _op(effect) != ToolOperation.EFFECT:
                continue
            for r in effect.resources:
                key = r.identity or r.resource_id
                if key in check_keys:
                    pairs.append((check, effect, key))
    return pairs


def _filtered(
    workflow: Workflow, suppress: Callable[[Node, str], bool] | None
) -> frozenset[Triple]:
    return frozenset(
        (c.node_id, e.node_id, key)
        for c, e, key in _reachable_pairs(workflow)
        if suppress is None or not suppress(e, key)
    )


def _b2(workflow: Workflow) -> frozenset[Triple]:
    return _filtered(workflow, None)


def _b3(workflow: Workflow) -> frozenset[Triple]:
    def any_binding(effect: Node, _key: str) -> bool:
        return any(b.mechanism != BindingMechanism.NONE for b in effect.bindings)

    return _filtered(workflow, any_binding)


def _b3a(workflow: Workflow) -> frozenset[Triple]:
    def authority_binding(effect: Node, _key: str) -> bool:
        contract = effect.contract
        enforced = (
            contract is not None and contract.authority_behavior == AuthorityBehavior.ENFORCED
        )
        return enforced and any(
            b.mechanism != BindingMechanism.NONE and b.authority_enforced for b in effect.bindings
        )

    return _filtered(workflow, authority_binding)


_BASELINES: dict[str, Callable[[Workflow], frozenset[Triple]]] = {
    "B1": _b1,
    "B2": _b2,
    "B3": _b3,
    "B3A": _b3a,
}
