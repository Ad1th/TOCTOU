"""Tests for the M2.1 workflow IR foundation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from agentlint.contracts.models import (
    AuthorityBehavior,
    BindingMechanism,
    ToolContract,
    ToolOperation,
)
from agentlint.ir import (
    BindingReference,
    Edge,
    EdgeKind,
    FindingLocation,
    GraphCycleError,
    GraphValidationError,
    Node,
    NodeKind,
    ResourceReference,
    ResourceType,
    Workflow,
)


def test_workflow_construction_and_contract_attachment() -> None:
    """A valid workflow can attach M1 ToolContract objects to tool-call nodes."""

    contract = ToolContract(
        contract_id="kv_version.debit_with_cas",
        operation=ToolOperation.EFFECT,
        resource_argument="key",
        predicate=None,
        binding_mechanisms=(BindingMechanism.VERSION,),
        authority_behavior=AuthorityBehavior.ENFORCED,
        version_argument="expected_version",
        effect_category="debit",
        safety_oracle="no_overdraft",
    )
    resource = ResourceReference(
        resource_id="account:123",
        argument_name="key",
        resource_type=ResourceType.KEY_VALUE,
        identity="account:123@v1",
    )
    binding = BindingReference(
        mechanism=BindingMechanism.VERSION,
        contract_id=contract.contract_id,
        authority_enforced=True,
    )
    workflow = Workflow(
        workflow_id="valid_workflow",
        nodes=(
            Node(node_id="start", kind=NodeKind.START),
            Node(
                node_id="debit",
                kind=NodeKind.TOOL_CALL,
                contract=contract,
                resources=(resource,),
                bindings=(binding,),
                provenance=("fixture.py:10",),
            ),
            Node(node_id="end", kind=NodeKind.END),
        ),
        edges=(
            Edge(edge_id="e1", source_id="start", target_id="debit"),
            Edge(edge_id="e2", source_id="debit", target_id="end"),
        ),
    )

    assert workflow.node("debit").contract == contract
    assert workflow.node("debit").resources == (resource,)
    assert workflow.node("debit").bindings == (binding,)


def test_predecessor_successor_and_topological_order_are_deterministic() -> None:
    """Traversal preserves deterministic node and edge order."""

    workflow = _branching_workflow()

    assert [node.node_id for node in workflow.successors("start")] == ["left", "right"]
    assert [node.node_id for node in workflow.predecessors("end")] == ["left", "right"]
    assert [node.node_id for node in workflow.topological_order()] == [
        "start",
        "left",
        "right",
        "end",
    ]


def test_node_lookup_rejects_unknown_identifier() -> None:
    """Node lookup fails explicitly for unknown IDs."""

    with pytest.raises(KeyError):
        _branching_workflow().node("missing")


def test_duplicate_nodes_are_rejected() -> None:
    """Duplicate node IDs are invalid."""

    with pytest.raises(GraphValidationError):
        Workflow(
            workflow_id="duplicate_nodes",
            nodes=(
                Node(node_id="n1", kind=NodeKind.START),
                Node(node_id="n1", kind=NodeKind.END),
            ),
        )


def test_duplicate_edges_are_rejected() -> None:
    """Duplicate edge IDs are invalid."""

    with pytest.raises(GraphValidationError):
        Workflow(
            workflow_id="duplicate_edges",
            nodes=(
                Node(node_id="n1", kind=NodeKind.START),
                Node(node_id="n2", kind=NodeKind.END),
            ),
            edges=(
                Edge(edge_id="e1", source_id="n1", target_id="n2"),
                Edge(edge_id="e1", source_id="n1", target_id="n2"),
            ),
        )


def test_invalid_edges_are_rejected() -> None:
    """Edges must reference existing source and target node IDs."""

    with pytest.raises(GraphValidationError):
        Workflow(
            workflow_id="invalid_edge",
            nodes=(Node(node_id="n1", kind=NodeKind.START),),
            edges=(Edge(edge_id="e1", source_id="n1", target_id="missing"),),
        )


def test_cycles_are_allowed_but_rejected_by_topological_order() -> None:
    """The IR can represent cyclic workflows, but topological ordering reports cycles."""

    workflow = Workflow(
        workflow_id="cycle",
        nodes=(
            Node(node_id="a", kind=NodeKind.COMPUTE),
            Node(node_id="b", kind=NodeKind.COMPUTE),
        ),
        edges=(
            Edge(edge_id="e1", source_id="a", target_id="b"),
            Edge(edge_id="e2", source_id="b", target_id="a"),
        ),
    )

    with pytest.raises(GraphCycleError):
        workflow.topological_order()


def test_ir_models_are_immutable() -> None:
    """IR dataclasses are frozen after construction."""

    node = Node(node_id="start", kind=NodeKind.START)

    with pytest.raises(FrozenInstanceError):
        node.node_id = "changed"  # type: ignore[misc]


def test_finding_location_validates_identifiers() -> None:
    """FindingLocation is available for future finding provenance."""

    location = FindingLocation(
        workflow_id="wf",
        node_id="n1",
        edge_id="e1",
        source="fixture.py:12",
    )

    assert location.workflow_id == "wf"


def _branching_workflow() -> Workflow:
    return Workflow(
        workflow_id="branching",
        nodes=(
            Node(node_id="start", kind=NodeKind.START),
            Node(node_id="left", kind=NodeKind.COMPUTE),
            Node(node_id="right", kind=NodeKind.COMPUTE),
            Node(node_id="end", kind=NodeKind.END),
        ),
        edges=(
            Edge(edge_id="e1", source_id="start", target_id="left", kind=EdgeKind.CONTROL),
            Edge(edge_id="e2", source_id="start", target_id="right", kind=EdgeKind.CONTROL),
            Edge(edge_id="e3", source_id="left", target_id="end", kind=EdgeKind.CONTROL),
            Edge(edge_id="e4", source_id="right", target_id="end", kind=EdgeKind.CONTROL),
        ),
    )
