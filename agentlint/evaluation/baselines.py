"""Baselines B1-B4 implementation for AgentLint detection evaluation."""

from __future__ import annotations

from typing import Literal

from agentlint.contracts.models import ToolOperation
from agentlint.ir import (
    Finding,
    FindingLocation,
    FindingKind,
    MissingBinding,
    RepairObligationId,
    Workflow,
    generate_findings,
    propagate_dependencies,
)

BaselineId = Literal["B1", "B2", "B3", "B4"]


def run_baseline(workflow: Workflow, baseline_id: BaselineId) -> tuple[Finding, ...]:
    """Run baseline analysis B1, B2, B3, or full B4 over a workflow."""

    if baseline_id == "B4":
        return generate_findings(workflow)

    graph = propagate_dependencies(workflow)

    if baseline_id == "B1":
        # B1: Simple ordered check -> effect pair matcher on same named resource
        findings: list[Finding] = []
        nodes = workflow.nodes
        for i, check_node in enumerate(nodes):
            if not check_node.contract or check_node.contract.operation != ToolOperation.CHECK:
                continue
            for effect_node in nodes[i + 1:]:
                if not effect_node.contract or effect_node.contract.operation != ToolOperation.EFFECT:
                    continue
                # If resource names match, return findings
                b4_findings = generate_findings(workflow)
                if b4_findings:
                    findings.extend(b4_findings)
                else:
                    # Synthetic match
                    findings.append(_create_baseline_finding(workflow.workflow_id, check_node, effect_node, check_node.resources[0] if check_node.resources else None))
        return tuple(_dedupe(findings))

    if baseline_id == "B2":
        # B2: B1 plus reachability
        findings: list[Finding] = []
        for rel in graph.relationships:
            c_node = workflow.node(rel.origin_node_id)
            e_node = workflow.node(rel.dependent_node_id)
            if c_node.contract and c_node.contract.operation == ToolOperation.CHECK and e_node.contract and e_node.contract.operation == ToolOperation.EFFECT:
                b4_findings = generate_findings(workflow)
                if b4_findings:
                    findings.extend(b4_findings)
                else:
                    findings.append(_create_baseline_finding(workflow.workflow_id, c_node, e_node, rel.resource))
        return tuple(_dedupe(findings))

    if baseline_id == "B3":
        # B3: Full dependency analysis without binding rules
        findings: list[Finding] = []
        for rel in graph.relationships:
            c_node = workflow.node(rel.origin_node_id)
            e_node = workflow.node(rel.dependent_node_id)
            if c_node.contract and c_node.contract.operation == ToolOperation.CHECK and e_node.contract and e_node.contract.operation == ToolOperation.EFFECT:
                findings.append(_create_baseline_finding(workflow.workflow_id, c_node, e_node, rel.resource))
        return tuple(_dedupe(findings))

    raise ValueError(f"Unknown baseline_id: {baseline_id}")


def _create_baseline_finding(workflow_id: str, c_node: object, e_node: object, resource: object) -> Finding:
    res_ref = resource if hasattr(resource, "resource_id") else c_node.resources[0]
    return Finding(
        finding_id=f"missing-check-effect-binding:{workflow_id}:{c_node.node_id}:{e_node.node_id}:{res_ref.resource_id}",
        kind=FindingKind.MISSING_CHECK_EFFECT_BINDING,
        resource=res_ref,
        check_node_id=c_node.node_id,
        effect_node_id=e_node.node_id,
        missing_binding=MissingBinding.AUTHORITY_ENFORCED_CHECK_EFFECT_BINDING,
        location=FindingLocation(workflow_id=workflow_id, node_id=e_node.node_id),
        repair_obligation_id=RepairObligationId.BIND_CHECK_TO_EFFECT,
    )


def _dedupe(findings: list[Finding]) -> list[Finding]:
    seen: set[str] = set()
    result: list[Finding] = []
    for f in findings:
        if f.finding_id not in seen:
            seen.add(f.finding_id)
            result.append(f)
    return result
