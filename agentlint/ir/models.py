"""Immutable directed workflow graph models for AgentLint."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum

from agentlint.contracts.models import BindingMechanism, ToolContract


class GraphValidationError(ValueError):
    """Raised when a workflow graph is structurally invalid."""


class GraphCycleError(GraphValidationError):
    """Raised when a topological order is requested for a cyclic graph."""


class NodeKind(StrEnum):
    """Supported workflow node categories."""

    START = "start"
    END = "end"
    TOOL_CALL = "tool_call"
    DECISION = "decision"
    COMPUTE = "compute"
    UNKNOWN = "unknown"


class EdgeKind(StrEnum):
    """Supported directed edge categories."""

    CONTROL = "control"
    DATA = "data"
    DEPENDENCY = "dependency"
    UNKNOWN = "unknown"


class ResourceType(StrEnum):
    """Resource identity categories carried by workflow nodes."""

    FILE = "file"
    KEY_VALUE = "key_value"
    HTTP = "http"
    AUTHORITY = "authority"
    WORKFLOW = "workflow"
    DATABASE = "database"
    CLOUD_OBJECT = "cloud_object"
    GIT = "git"
    QUEUE = "queue"
    CLUSTER = "cluster"
    PAYMENT = "payment"
    CHANNEL = "channel"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ResourceReference:
    """A normalized reference to a workflow resource."""

    resource_id: str
    argument_name: str
    resource_type: ResourceType = ResourceType.UNKNOWN
    identity: str | None = None

    @property
    def key(self) -> str:
        """Canonical identity used to match a check and an effect on the same resource."""

        return self.identity if self.identity is not None else self.resource_id

    def __post_init__(self) -> None:
        _require_identifier(self.resource_id, "resource_id")
        _require_identifier(self.argument_name, "argument_name")
        if self.identity is not None:
            _require_identifier(self.identity, "identity")


@dataclass(frozen=True, slots=True)
class BindingReference:
    """A modeled binding mechanism attached to a node or effect."""

    mechanism: BindingMechanism
    contract_id: str
    authority_enforced: bool
    description: str | None = None
    resource_id: str | None = None
    """Resource key the binding protects; ``None`` scopes it to every resource of its node."""

    def __post_init__(self) -> None:
        _require_identifier(self.contract_id, "contract_id")
        if self.description is not None:
            _require_identifier(self.description, "description")
        if self.resource_id is not None:
            _require_identifier(self.resource_id, "resource_id")


@dataclass(frozen=True, slots=True)
class FindingLocation:
    """Source location for future findings over the workflow graph."""

    workflow_id: str
    node_id: str | None = None
    edge_id: str | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.workflow_id, "workflow_id")
        for field_name, value in (
            ("node_id", self.node_id),
            ("edge_id", self.edge_id),
            ("source", self.source),
        ):
            if value is not None:
                _require_identifier(value, field_name)


@dataclass(frozen=True, slots=True)
class Node:
    """A node in the internal workflow graph."""

    node_id: str
    kind: NodeKind
    label: str | None = None
    contract: ToolContract | None = None
    resources: tuple[ResourceReference, ...] = field(default_factory=tuple)
    bindings: tuple[BindingReference, ...] = field(default_factory=tuple)
    provenance: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _require_identifier(self.node_id, "node_id")
        if self.label is not None:
            _require_identifier(self.label, "label")
        _require_all(self.resources, ResourceReference, "resources")
        _require_all(self.bindings, BindingReference, "bindings")
        _require_text_tuple(self.provenance, "provenance")


@dataclass(frozen=True, slots=True)
class Edge:
    """A directed edge between two workflow nodes."""

    edge_id: str
    source_id: str
    target_id: str
    kind: EdgeKind = EdgeKind.CONTROL
    label: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.edge_id, "edge_id")
        _require_identifier(self.source_id, "source_id")
        _require_identifier(self.target_id, "target_id")
        if self.label is not None:
            _require_identifier(self.label, "label")


@dataclass(frozen=True, slots=True)
class Workflow:
    """An immutable directed graph of workflow nodes and edges."""

    workflow_id: str
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...] = field(default_factory=tuple)
    _index: dict[str, int] = field(init=False, repr=False, compare=False, hash=False)
    _preds: dict[str, tuple[str, ...]] = field(init=False, repr=False, compare=False, hash=False)
    _succs: dict[str, tuple[str, ...]] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        _require_identifier(self.workflow_id, "workflow_id")
        _require_all(self.nodes, Node, "nodes")
        _require_all(self.edges, Edge, "edges")
        if not self.nodes:
            raise GraphValidationError("workflow must contain at least one node")

        node_ids = [node.node_id for node in self.nodes]
        duplicate_nodes = _duplicates(node_ids)
        if duplicate_nodes:
            raise GraphValidationError(f"duplicate node id(s): {', '.join(duplicate_nodes)}")

        edge_ids = [edge.edge_id for edge in self.edges]
        duplicate_edges = _duplicates(edge_ids)
        if duplicate_edges:
            raise GraphValidationError(f"duplicate edge id(s): {', '.join(duplicate_edges)}")

        node_id_set = set(node_ids)
        invalid_edges = [
            edge.edge_id
            for edge in self.edges
            if edge.source_id not in node_id_set or edge.target_id not in node_id_set
        ]
        if invalid_edges:
            raise GraphValidationError(
                f"edge(s) reference unknown node(s): {', '.join(invalid_edges)}"
            )

        preds: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
        succs: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
        for edge in self.edges:
            preds[edge.target_id].append(edge.source_id)
            succs[edge.source_id].append(edge.target_id)
        object.__setattr__(self, "_index", {node_id: i for i, node_id in enumerate(node_ids)})
        object.__setattr__(self, "_preds", {k: tuple(v) for k, v in preds.items()})
        object.__setattr__(self, "_succs", {k: tuple(v) for k, v in succs.items()})

    def node(self, node_id: str) -> Node:
        """Return a node by identifier in O(1)."""

        return self.nodes[self._index[node_id]]

    def predecessor_ids(self, node_id: str) -> tuple[str, ...]:
        """Return direct predecessor identifiers in deterministic edge order."""

        return self._preds[node_id]

    def successor_ids(self, node_id: str) -> tuple[str, ...]:
        """Return direct successor identifiers in deterministic edge order."""

        return self._succs[node_id]

    def predecessors(self, node_id: str) -> tuple[Node, ...]:
        """Return direct predecessor nodes in deterministic edge order."""

        return tuple(self.node(predecessor_id) for predecessor_id in self._preds[node_id])

    def successors(self, node_id: str) -> tuple[Node, ...]:
        """Return direct successor nodes in deterministic edge order."""

        return tuple(self.node(successor_id) for successor_id in self._succs[node_id])

    def is_acyclic(self) -> bool:
        """Return whether the workflow graph contains no directed cycle."""

        try:
            self.topological_order()
        except GraphCycleError:
            return False
        return True

    def topological_order(self) -> tuple[Node, ...]:
        """Return a deterministic topological ordering for an acyclic workflow."""

        in_degree = {node.node_id: 0 for node in self.nodes}
        successors: dict[str, list[str]] = {node.node_id: [] for node in self.nodes}
        for edge in self.edges:
            in_degree[edge.target_id] += 1
            successors[edge.source_id].append(edge.target_id)

        ready = deque(node.node_id for node in self.nodes if in_degree[node.node_id] == 0)
        ordered_ids: list[str] = []
        while ready:
            node_id = ready.popleft()
            ordered_ids.append(node_id)
            for successor_id in successors[node_id]:
                in_degree[successor_id] -= 1
                if in_degree[successor_id] == 0:
                    ready.append(successor_id)

        if len(ordered_ids) != len(self.nodes):
            raise GraphCycleError("workflow contains a cycle")
        return tuple(self.node(node_id) for node_id in ordered_ids)


def _require_identifier(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise GraphValidationError(f"{field_name} must be a non-empty string")


def _require_all[T](values: tuple[object, ...], expected_type: type[T], field_name: str) -> None:
    if not isinstance(values, tuple):
        raise GraphValidationError(f"{field_name} must be a tuple")
    if not all(isinstance(value, expected_type) for value in values):
        raise GraphValidationError(f"{field_name} entries must be {expected_type.__name__}")


def _require_text_tuple(values: tuple[str, ...], field_name: str) -> None:
    if not isinstance(values, tuple):
        raise GraphValidationError(f"{field_name} must be a tuple")
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise GraphValidationError(f"{field_name} entries must be non-empty strings")


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates
