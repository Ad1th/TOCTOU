"""Tests for M2.2 workflow dependency propagation."""

from __future__ import annotations

import pytest

from agentlint.contracts.models import BindingMechanism
from agentlint.ir import (
    BindingReference,
    Edge,
    GraphCycleError,
    Node,
    NodeKind,
    ResourceReference,
    ResourceType,
    Workflow,
    propagate_dependencies,
)


def test_dependency_propagates_through_branching_workflow() -> None:
    """A source resource reaches both branch nodes deterministically."""

    resource = ResourceReference(
        resource_id="account:123",
        argument_name="key",
        resource_type=ResourceType.KEY_VALUE,
    )
    workflow = Workflow(
        workflow_id="branching_dependency",
        nodes=(
            Node(node_id="start", kind=NodeKind.START, resources=(resource,)),
            Node(node_id="left", kind=NodeKind.COMPUTE),
            Node(node_id="right", kind=NodeKind.COMPUTE),
            Node(node_id="end", kind=NodeKind.END),
        ),
        edges=(
            Edge(edge_id="e1", source_id="start", target_id="left"),
            Edge(edge_id="e2", source_id="start", target_id="right"),
            Edge(edge_id="e3", source_id="left", target_id="end"),
            Edge(edge_id="e4", source_id="right", target_id="end"),
        ),
    )

    dependency_graph = propagate_dependencies(workflow)

    assert [
        propagated.resource.resource_id for propagated in dependency_graph.resources_at("left")
    ] == ["account:123"]
    assert [
        propagated.resource.resource_id for propagated in dependency_graph.resources_at("right")
    ] == ["account:123"]
    assert [relationship.dependent_node_id for relationship in dependency_graph.relationships] == [
        "left",
        "right",
        "end",
    ]


def test_dependency_propagation_deduplicates_at_merge_points() -> None:
    """A resource arriving through two branches appears once at the merge node."""

    resource = ResourceReference(resource_id="file:/tmp/a", argument_name="path")
    workflow = Workflow(
        workflow_id="merge_dependency",
        nodes=(
            Node(node_id="source", kind=NodeKind.TOOL_CALL, resources=(resource,)),
            Node(node_id="left", kind=NodeKind.COMPUTE),
            Node(node_id="right", kind=NodeKind.COMPUTE),
            Node(node_id="merge", kind=NodeKind.COMPUTE),
        ),
        edges=(
            Edge(edge_id="e1", source_id="source", target_id="left"),
            Edge(edge_id="e2", source_id="source", target_id="right"),
            Edge(edge_id="e3", source_id="left", target_id="merge"),
            Edge(edge_id="e4", source_id="right", target_id="merge"),
        ),
    )

    dependency_graph = propagate_dependencies(workflow)

    assert dependency_graph.resources_at("merge") == dependency_graph.resources_at("left")
    assert [
        relationship.origin_node_id for relationship in dependency_graph.dependencies_of("merge")
    ] == ["source"]


def test_multiple_resources_propagate_in_stable_order() -> None:
    """Multiple resources retain their original deterministic order."""

    first = ResourceReference(resource_id="file:/tmp/a", argument_name="path")
    second = ResourceReference(
        resource_id="https://service/item/1",
        argument_name="item_url",
        resource_type=ResourceType.HTTP,
    )
    workflow = Workflow(
        workflow_id="multiple_resources",
        nodes=(
            Node(node_id="first", kind=NodeKind.TOOL_CALL, resources=(first,)),
            Node(node_id="second", kind=NodeKind.TOOL_CALL, resources=(second,)),
            Node(node_id="effect", kind=NodeKind.TOOL_CALL),
        ),
        edges=(
            Edge(edge_id="e1", source_id="first", target_id="second"),
            Edge(edge_id="e2", source_id="second", target_id="effect"),
        ),
    )

    dependency_graph = propagate_dependencies(workflow)

    assert [
        propagated.resource.resource_id for propagated in dependency_graph.resources_at("effect")
    ] == ["file:/tmp/a", "https://service/item/1"]


def test_binding_metadata_is_preserved_during_propagation() -> None:
    """Binding references propagate independently of contract evaluation."""

    binding = BindingReference(
        mechanism=BindingMechanism.VERSION,
        contract_id="kv_version.debit_with_cas",
        authority_enforced=True,
        description="checked version token",
    )
    workflow = Workflow(
        workflow_id="binding_metadata",
        nodes=(
            Node(node_id="check", kind=NodeKind.TOOL_CALL, bindings=(binding,)),
            Node(node_id="effect", kind=NodeKind.TOOL_CALL),
        ),
        edges=(Edge(edge_id="e1", source_id="check", target_id="effect"),),
    )

    dependency_graph = propagate_dependencies(workflow)

    assert dependency_graph.bindings_at("effect")[0].origin_node_id == "check"
    assert dependency_graph.bindings_at("effect")[0].binding == binding


def test_dependency_output_is_deterministic() -> None:
    """Repeated propagation over the same workflow produces identical output."""

    workflow = Workflow(
        workflow_id="deterministic",
        nodes=(
            Node(
                node_id="a",
                kind=NodeKind.TOOL_CALL,
                resources=(ResourceReference(resource_id="r1", argument_name="arg"),),
            ),
            Node(
                node_id="b",
                kind=NodeKind.TOOL_CALL,
                resources=(ResourceReference(resource_id="r2", argument_name="arg"),),
            ),
            Node(node_id="c", kind=NodeKind.COMPUTE),
        ),
        edges=(
            Edge(edge_id="e1", source_id="a", target_id="c"),
            Edge(edge_id="e2", source_id="b", target_id="c"),
        ),
    )

    assert propagate_dependencies(workflow) == propagate_dependencies(workflow)


def test_dependency_propagation_requires_topological_workflow() -> None:
    """Cycles remain unsupported for dependency propagation."""

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
        propagate_dependencies(workflow)
