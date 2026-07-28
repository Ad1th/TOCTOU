"""Typed dependency propagation over the workflow IR."""

from __future__ import annotations

from dataclasses import dataclass, field

from agentlint.ir.models import BindingReference, GraphValidationError, ResourceReference, Workflow


@dataclass(frozen=True, slots=True)
class PropagatedResource:
    """A resource reference propagated from its origin node."""

    origin_node_id: str
    resource: ResourceReference

    def __post_init__(self) -> None:
        _require_identifier(self.origin_node_id, "origin_node_id")


@dataclass(frozen=True, slots=True)
class PropagatedBinding:
    """A binding reference propagated from its origin node."""

    origin_node_id: str
    binding: BindingReference

    def __post_init__(self) -> None:
        _require_identifier(self.origin_node_id, "origin_node_id")


@dataclass(frozen=True, slots=True)
class NodeDependencyState:
    """Resources and bindings available at one workflow node after propagation."""

    node_id: str
    resources: tuple[PropagatedResource, ...] = field(default_factory=tuple)
    bindings: tuple[PropagatedBinding, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_identifier(self.node_id, "node_id")


@dataclass(frozen=True, slots=True)
class DependencyRelationship:
    """A resource dependency from an origin node to a dependent node."""

    origin_node_id: str
    dependent_node_id: str
    resource: ResourceReference
    bindings: tuple[PropagatedBinding, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_identifier(self.origin_node_id, "origin_node_id")
        _require_identifier(self.dependent_node_id, "dependent_node_id")


@dataclass(frozen=True, slots=True)
class DependencyGraph:
    """Deterministic dependency state derived from a workflow graph."""

    workflow_id: str
    node_states: tuple[NodeDependencyState, ...]
    relationships: tuple[DependencyRelationship, ...]

    def state_for(self, node_id: str) -> NodeDependencyState:
        """Return propagated dependency state for a node."""

        for state in self.node_states:
            if state.node_id == node_id:
                return state
        raise KeyError(node_id)

    def resources_at(self, node_id: str) -> tuple[PropagatedResource, ...]:
        """Return resources available at a node."""

        return self.state_for(node_id).resources

    def bindings_at(self, node_id: str) -> tuple[PropagatedBinding, ...]:
        """Return bindings available at a node."""

        return self.state_for(node_id).bindings

    def dependencies_of(self, node_id: str) -> tuple[DependencyRelationship, ...]:
        """Return resource dependencies whose dependent node is `node_id`."""

        self.state_for(node_id)
        return tuple(
            relationship
            for relationship in self.relationships
            if relationship.dependent_node_id == node_id
        )


def propagate_dependencies(workflow: Workflow) -> DependencyGraph:
    """Propagate resources and bindings over an acyclic workflow."""

    ordered_nodes = workflow.topological_order()
    states: dict[str, NodeDependencyState] = {}
    relationships: list[DependencyRelationship] = []

    for node in ordered_nodes:
        incoming_resources: list[PropagatedResource] = []
        incoming_bindings: list[PropagatedBinding] = []
        for predecessor in workflow.predecessors(node.node_id):
            predecessor_state = states[predecessor.node_id]
            incoming_resources.extend(predecessor_state.resources)
            incoming_bindings.extend(predecessor_state.bindings)

        direct_resources = [
            PropagatedResource(origin_node_id=node.node_id, resource=resource)
            for resource in node.resources
        ]
        direct_bindings = [
            PropagatedBinding(origin_node_id=node.node_id, binding=binding)
            for binding in node.bindings
        ]
        resources = _dedupe(incoming_resources + direct_resources)
        bindings = _dedupe(incoming_bindings + direct_bindings)
        states[node.node_id] = NodeDependencyState(
            node_id=node.node_id,
            resources=resources,
            bindings=bindings,
        )

        for propagated_resource in resources:
            if propagated_resource.origin_node_id != node.node_id:
                relationships.append(
                    DependencyRelationship(
                        origin_node_id=propagated_resource.origin_node_id,
                        dependent_node_id=node.node_id,
                        resource=propagated_resource.resource,
                        bindings=bindings,
                    )
                )

    return DependencyGraph(
        workflow_id=workflow.workflow_id,
        node_states=tuple(states[node.node_id] for node in ordered_nodes),
        relationships=tuple(relationships),
    )


def _dedupe[T](values: list[T]) -> tuple[T, ...]:
    deduped: list[T] = []
    seen: set[T] = set()
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return tuple(deduped)


def _require_identifier(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise GraphValidationError(f"{field_name} must be a non-empty string")
