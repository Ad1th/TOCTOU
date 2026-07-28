"""Load evaluation workflow fixtures into the existing Workflow IR."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from agentlint.contracts import ToolContract, load_contract
from agentlint.contracts.models import BindingMechanism
from agentlint.evaluation.models import WorkflowCase
from agentlint.ir import (
    BindingReference,
    Edge,
    EdgeKind,
    Node,
    NodeKind,
    ResourceReference,
    ResourceType,
    Workflow,
)


class WorkflowFixtureError(ValueError):
    """Raised when an evaluation workflow fixture is malformed."""


def load_contracts(contracts_dir: Path) -> dict[str, ToolContract]:
    """Load all contract fixtures from a directory keyed by contract ID."""

    contracts = [load_contract(path) for path in sorted(contracts_dir.glob("*.json"))]
    return {contract.contract_id: contract for contract in contracts}


def load_workflow_cases(
    path: Path, contracts: Mapping[str, ToolContract]
) -> tuple[WorkflowCase, ...]:
    """Load workflow cases from a fixture file or directory."""

    fixture_paths = tuple(sorted(path.glob("*.json"))) if path.is_dir() else (path,)
    cases: list[WorkflowCase] = []
    for fixture_path in fixture_paths:
        document = json.loads(fixture_path.read_text(encoding="utf-8"))
        workflows = document.get("workflows") if isinstance(document, Mapping) else None
        if isinstance(workflows, str) or not isinstance(workflows, Sequence):
            raise WorkflowFixtureError("workflow fixture must contain a workflows list")
        cases.extend(_workflow_case(workflow, contracts) for workflow in workflows)
    return tuple(cases)


def _workflow_case(document: object, contracts: Mapping[str, ToolContract]) -> WorkflowCase:
    if not isinstance(document, Mapping):
        raise WorkflowFixtureError("workflow entries must be objects")

    workflow_id = _required_text(document, "workflow_id")
    nodes = tuple(_node(node_document, contracts) for node_document in _sequence(document, "nodes"))
    edges = tuple(_edge(edge_document) for edge_document in _sequence(document, "edges"))
    workflow = Workflow(workflow_id=workflow_id, nodes=nodes, edges=edges)
    return WorkflowCase(
        workflow_id=workflow_id,
        family_id=_required_text(document, "family_id"),
        variant=_required_text(document, "variant"),
        workflow=workflow,
    )


def _node(document: object, contracts: Mapping[str, ToolContract]) -> Node:
    if not isinstance(document, Mapping):
        raise WorkflowFixtureError("node entries must be objects")
    contract_id = document.get("contract_id")
    contract = None
    if contract_id is not None:
        if not isinstance(contract_id, str) or contract_id not in contracts:
            raise WorkflowFixtureError(f"unknown contract_id: {contract_id}")
        contract = contracts[contract_id]
    return Node(
        node_id=_required_text(document, "node_id"),
        kind=NodeKind(_required_text(document, "kind")),
        contract=contract,
        resources=tuple(_resource(resource) for resource in _sequence(document, "resources")),
        bindings=tuple(_binding(binding) for binding in _sequence(document, "bindings")),
    )


def _edge(document: object) -> Edge:
    if not isinstance(document, Mapping):
        raise WorkflowFixtureError("edge entries must be objects")
    return Edge(
        edge_id=_required_text(document, "edge_id"),
        source_id=_required_text(document, "source_id"),
        target_id=_required_text(document, "target_id"),
        kind=EdgeKind(_optional_text(document, "kind", EdgeKind.CONTROL.value)),
    )


def _resource(document: object) -> ResourceReference:
    if not isinstance(document, Mapping):
        raise WorkflowFixtureError("resource entries must be objects")
    return ResourceReference(
        resource_id=_required_text(document, "resource_id"),
        argument_name=_required_text(document, "argument_name"),
        resource_type=ResourceType(_optional_text(document, "resource_type", ResourceType.UNKNOWN)),
        identity=_nullable_text(document, "identity"),
    )


def _binding(document: object) -> BindingReference:
    if not isinstance(document, Mapping):
        raise WorkflowFixtureError("binding entries must be objects")
    return BindingReference(
        mechanism=BindingMechanism(_required_text(document, "mechanism")),
        contract_id=_required_text(document, "contract_id"),
        authority_enforced=_required_bool(document, "authority_enforced"),
        description=_nullable_text(document, "description"),
    )


def _sequence(document: Mapping[str, Any], field_name: str) -> tuple[object, ...]:
    value = document.get(field_name, [])
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise WorkflowFixtureError(f"{field_name} must be a list")
    return tuple(value)


def _required_text(document: Mapping[str, Any], field_name: str) -> str:
    value = document.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise WorkflowFixtureError(f"{field_name} must be a non-empty string")
    return value


def _optional_text(document: Mapping[str, Any], field_name: str, default: str) -> str:
    value = document.get(field_name, default)
    if not isinstance(value, str) or not value.strip():
        raise WorkflowFixtureError(f"{field_name} must be a non-empty string")
    return value


def _nullable_text(document: Mapping[str, Any], field_name: str) -> str | None:
    value = document.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise WorkflowFixtureError(f"{field_name} must be null or a non-empty string")
    return value


def _required_bool(document: Mapping[str, Any], field_name: str) -> bool:
    value = document.get(field_name)
    if not isinstance(value, bool):
        raise WorkflowFixtureError(f"{field_name} must be a boolean")
    return value
