"""Finding generation: resource-keyed check-effect binding analysis.

A finding is reported for a pair (c, e, r) when

* ``c`` is a node whose contract operation is ``check`` and which declares resource ``r``;
* ``e`` is a node whose contract operation is ``effect`` and which declares a resource with
  the same canonical key as ``r``;
* ``e`` is reachable from ``c`` in the workflow graph (cycles are allowed); and
* no *effective* binding for ``r`` exists at ``e``.

A binding at ``e`` is effective for ``r`` when it is attached to ``e`` itself (not inherited
from an unrelated upstream node), is scoped to ``r`` (or unscoped), uses a mechanism other
than ``none``, claims authority enforcement, and -- when ``e`` carries a contract -- the
contract confirms that the resource authority enforces that mechanism.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum

from agentlint.contracts.models import (
    AuthorityBehavior,
    BindingMechanism,
    ToolContract,
    ToolOperation,
)
from agentlint.ir.dependencies import DependencyGraph
from agentlint.ir.models import (
    BindingReference,
    FindingLocation,
    GraphValidationError,
    Node,
    ResourceReference,
    Workflow,
)


class FindingKind(StrEnum):
    """Supported finding categories."""

    MISSING_CHECK_EFFECT_BINDING = "missing_check_effect_binding"


class MissingBinding(StrEnum):
    """Missing relationship types."""

    AUTHORITY_ENFORCED_CHECK_EFFECT_BINDING = "authority_enforced_check_effect_binding"


class RepairObligationId(StrEnum):
    """Repair obligation identifiers referenced by findings."""

    BIND_CHECK_TO_EFFECT = "bind_check_to_effect"


@dataclass(frozen=True, slots=True)
class Finding:
    """A deterministic missing-binding finding between a check and effect node."""

    finding_id: str
    kind: FindingKind
    resource: ResourceReference
    check_node_id: str
    effect_node_id: str
    missing_binding: MissingBinding
    location: FindingLocation
    repair_obligation_id: RepairObligationId


# A propagated check fact: (check node id, checked resource).
_Fact = tuple[str, ResourceReference]


def generate_findings(
    workflow: Workflow,
    dependency_graph: DependencyGraph | None = None,
) -> tuple[Finding, ...]:
    """Generate missing check-effect binding findings for ``workflow``.

    ``dependency_graph`` is accepted for API compatibility and validated against the
    workflow, but the analysis uses its own resource-keyed propagation, which only tracks
    check facts and therefore stays near-linear on large graphs.
    """

    if dependency_graph is not None and dependency_graph.workflow_id != workflow.workflow_id:
        raise GraphValidationError("dependency graph workflow_id must match workflow workflow_id")

    facts, key_masks, incoming = _reaching_checks(workflow)
    findings: list[Finding] = []
    seen: set[str] = set()
    for effect_node in workflow.nodes:
        if _operation(effect_node.contract) != ToolOperation.EFFECT:
            continue
        reach = incoming.get(effect_node.node_id, 0)
        if not reach:
            continue
        for effect_resource in effect_node.resources:
            hits = reach & key_masks.get(effect_resource.key, 0)
            if not hits or is_discharged(effect_node, effect_resource.key):
                continue
            while hits:
                low = hits & -hits
                check_node_id, checked = facts[low.bit_length() - 1]
                hits ^= low
                finding_id = _finding_id(
                    workflow_id=workflow.workflow_id,
                    check_node_id=check_node_id,
                    effect_node_id=effect_node.node_id,
                    resource=checked,
                )
                if finding_id in seen:
                    continue
                seen.add(finding_id)
                findings.append(
                    Finding(
                        finding_id=finding_id,
                        kind=FindingKind.MISSING_CHECK_EFFECT_BINDING,
                        resource=checked,
                        check_node_id=check_node_id,
                        effect_node_id=effect_node.node_id,
                        missing_binding=MissingBinding.AUTHORITY_ENFORCED_CHECK_EFFECT_BINDING,
                        location=FindingLocation(
                            workflow_id=workflow.workflow_id,
                            node_id=effect_node.node_id,
                        ),
                        repair_obligation_id=RepairObligationId.BIND_CHECK_TO_EFFECT,
                    )
                )
    index = workflow._index
    findings.sort(key=lambda f: (index[f.check_node_id], index[f.effect_node_id]))
    return tuple(findings)


def is_discharged(effect_node: Node, resource_key: str) -> bool:
    """Return whether ``effect_node`` carries an effective binding for ``resource_key``."""

    return any(
        _binding_is_effective(binding, effect_node.contract, resource_key)
        for binding in effect_node.bindings
    )


def _binding_is_effective(
    binding: BindingReference,
    contract: ToolContract | None,
    resource_key: str,
) -> bool:
    if binding.mechanism == BindingMechanism.NONE or not binding.authority_enforced:
        return False
    if binding.resource_id is not None and binding.resource_id != resource_key:
        return False
    if contract is None:
        return True
    return (
        contract.authority_behavior == AuthorityBehavior.ENFORCED
        and binding.mechanism in contract.binding_mechanisms
    )


def _reaching_checks(
    workflow: Workflow,
) -> tuple[list[_Fact], dict[str, int], dict[str, int]]:
    """Compute, for every effect node, the set of check facts that reach it.

    A *fact* is one (check node, checked resource) pair, numbered in node order. Sets of
    facts are Python integers used as bitsets, so union is a single big-integer OR and
    states are shared rather than copied. Facts generated at a node become visible to its
    successors. Acyclic graphs are processed in one topological pass, releasing each
    node's state once all of its successors have consumed it; cyclic graphs use a monotone
    worklist iteration to a fixpoint.

    Returns the fact table, a mask of facts per resource key, and the incoming fact mask
    of every effect node.
    """

    facts: list[_Fact] = []
    key_masks: dict[str, int] = {}
    gen: dict[str, int] = {}
    for node in workflow.nodes:
        if _operation(node.contract) == ToolOperation.CHECK and node.resources:
            mask = 0
            for resource in node.resources:
                bit = 1 << len(facts)
                facts.append((node.node_id, resource))
                key_masks[resource.key] = key_masks.get(resource.key, 0) | bit
                mask |= bit
            gen[node.node_id] = mask
    effects = {n.node_id for n in workflow.nodes if _operation(n.contract) == ToolOperation.EFFECT}
    incoming: dict[str, int] = {}
    if not facts or not effects:
        return facts, key_masks, incoming

    if workflow.is_acyclic():
        out: dict[str, int] = {}
        pending = {n.node_id: len(workflow.successor_ids(n.node_id)) for n in workflow.nodes}
        for node in workflow.topological_order():
            node_id = node.node_id
            mask = 0
            for pred in workflow.predecessor_ids(node_id):
                mask |= out[pred]
                pending[pred] -= 1
                if pending[pred] == 0:
                    del out[pred]
            if node_id in effects:
                incoming[node_id] = mask
            if pending[node_id]:
                out[node_id] = mask | gen.get(node_id, 0)
        return facts, key_masks, incoming

    in_mask = {n.node_id: 0 for n in workflow.nodes}
    out_mask = {n.node_id: gen.get(n.node_id, 0) for n in workflow.nodes}
    work = deque(n.node_id for n in workflow.nodes)
    queued = set(work)
    while work:
        node_id = work.popleft()
        queued.discard(node_id)
        mask = 0
        for pred in workflow.predecessor_ids(node_id):
            mask |= out_mask[pred]
        if mask == in_mask[node_id] and out_mask[node_id] == (mask | gen.get(node_id, 0)):
            continue
        in_mask[node_id] = mask
        new_out = mask | gen.get(node_id, 0)
        if new_out != out_mask[node_id]:
            out_mask[node_id] = new_out
            for succ in workflow.successor_ids(node_id):
                if succ not in queued:
                    work.append(succ)
                    queued.add(succ)
    for node_id in effects:
        incoming[node_id] = in_mask[node_id]
    return facts, key_masks, incoming


def _operation(contract: ToolContract | None) -> ToolOperation | None:
    return contract.operation if contract is not None else None


def _finding_id(
    *,
    workflow_id: str,
    check_node_id: str,
    effect_node_id: str,
    resource: ResourceReference,
) -> str:
    return (
        "missing-check-effect-binding:"
        f"{workflow_id}:{check_node_id}:{effect_node_id}:{resource.resource_id}"
    )
