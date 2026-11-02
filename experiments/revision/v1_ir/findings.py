"""Finding generation over workflow dependency relationships."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from agentlint.contracts.models import BindingMechanism, ToolOperation
from experiments.revision.v1_ir.dependencies import (
    DependencyGraph,
    DependencyRelationship,
    propagate_dependencies,
)
from experiments.revision.v1_ir.models import (
    FindingLocation,
    GraphValidationError,
    ResourceReference,
    Workflow,
)


class FindingKind(StrEnum):
    """Supported finding categories for M2.3."""

    MISSING_CHECK_EFFECT_BINDING = "missing_check_effect_binding"


class MissingBinding(StrEnum):
    """Missing relationship types reported by M2.3."""

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


def generate_findings(
    workflow: Workflow,
    dependency_graph: DependencyGraph | None = None,
) -> tuple[Finding, ...]:
    """Generate missing check-effect binding findings from dependency relationships."""

    graph = dependency_graph if dependency_graph is not None else propagate_dependencies(workflow)
    if graph.workflow_id != workflow.workflow_id:
        raise GraphValidationError("dependency graph workflow_id must match workflow workflow_id")

    findings: list[Finding] = []
    for relationship in graph.relationships:
        check_node = workflow.node(relationship.origin_node_id)
        effect_node = workflow.node(relationship.dependent_node_id)
        if not _is_check_effect_pair(check_node.contract, effect_node.contract):
            continue
        if _has_authority_enforced_binding(relationship):
            continue
        findings.append(
            Finding(
                finding_id=_finding_id(
                    workflow_id=workflow.workflow_id,
                    check_node_id=check_node.node_id,
                    effect_node_id=effect_node.node_id,
                    resource=relationship.resource,
                ),
                kind=FindingKind.MISSING_CHECK_EFFECT_BINDING,
                resource=relationship.resource,
                check_node_id=check_node.node_id,
                effect_node_id=effect_node.node_id,
                missing_binding=MissingBinding.AUTHORITY_ENFORCED_CHECK_EFFECT_BINDING,
                location=FindingLocation(
                    workflow_id=workflow.workflow_id,
                    node_id=effect_node.node_id,
                ),
                repair_obligation_id=RepairObligationId.BIND_CHECK_TO_EFFECT,
            )
        )
    return tuple(_dedupe_findings(findings))


def _is_check_effect_pair(
    check_contract: object,
    effect_contract: object,
) -> bool:
    return (
        hasattr(check_contract, "operation")
        and hasattr(effect_contract, "operation")
        and check_contract.operation == ToolOperation.CHECK
        and effect_contract.operation == ToolOperation.EFFECT
    )


def _has_authority_enforced_binding(relationship: DependencyRelationship) -> bool:
    return any(
        propagated.binding.authority_enforced
        and propagated.binding.mechanism != BindingMechanism.NONE
        for propagated in relationship.bindings
    )


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


def _dedupe_findings(findings: list[Finding]) -> list[Finding]:
    deduped: list[Finding] = []
    seen: set[str] = set()
    for finding in findings:
        if finding.finding_id not in seen:
            deduped.append(finding)
            seen.add(finding.finding_id)
    return deduped
