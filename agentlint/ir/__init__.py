"""Workflow intermediate representation foundation."""

from agentlint.ir.dependencies import (
    DependencyGraph,
    DependencyRelationship,
    NodeDependencyState,
    PropagatedBinding,
    PropagatedResource,
    propagate_dependencies,
)
from agentlint.ir.findings import (
    Finding,
    FindingKind,
    MissingBinding,
    RepairObligationId,
    generate_findings,
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
    "Finding",
    "FindingKind",
    "FindingLocation",
    "GraphCycleError",
    "GraphValidationError",
    "MissingBinding",
    "Node",
    "NodeDependencyState",
    "NodeKind",
    "PropagatedBinding",
    "PropagatedResource",
    "ResourceReference",
    "ResourceType",
    "RepairObligationId",
    "Workflow",
    "generate_findings",
    "propagate_dependencies",
]
