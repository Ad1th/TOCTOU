"""Workflow intermediate representation foundation."""

from agentlint.ir.dependencies import (
    DependencyGraph,
    DependencyRelationship,
    NodeDependencyState,
    PropagatedBinding,
    PropagatedResource,
    propagate_dependencies,
)
from agentlint.ir.models import (
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

__all__ = [
    "BindingReference",
    "DependencyGraph",
    "DependencyRelationship",
    "Edge",
    "EdgeKind",
    "FindingLocation",
    "GraphCycleError",
    "GraphValidationError",
    "Node",
    "NodeDependencyState",
    "NodeKind",
    "PropagatedBinding",
    "PropagatedResource",
    "ResourceReference",
    "ResourceType",
    "Workflow",
    "propagate_dependencies",
]
