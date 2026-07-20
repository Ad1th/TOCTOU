"""Validation helpers for AgentLint tool-contract documents."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Any

from agentlint.contracts.models import (
    AuthorityBehavior,
    BindingMechanism,
    ToolContract,
    ToolOperation,
)

REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "contract_id",
        "operation",
        "resource_argument",
        "binding_mechanisms",
        "authority_behavior",
    }
)


class ContractValidationError(ValueError):
    """Raised when a contract document violates the M1 contract schema."""


def load_contract(path: Path) -> ToolContract:
    """Load and validate a JSON contract document from disk."""

    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ContractValidationError("contract document must be a JSON object")
    return validate_contract(document)


def validate_contract(document: Mapping[str, Any]) -> ToolContract:
    """Validate a contract document and return its typed representation."""

    missing = sorted(REQUIRED_FIELDS.difference(document))
    if missing:
        raise ContractValidationError(f"contract missing required field(s): {', '.join(missing)}")

    schema_version = document["schema_version"]
    if schema_version != 1:
        raise ContractValidationError("schema_version must be 1")

    contract_id = _required_text(document, "contract_id")
    operation = _enum_value(ToolOperation, _required_text(document, "operation"), "operation")
    resource_argument = _required_text(document, "resource_argument")
    predicate = _optional_text(document, "predicate")
    binding_mechanisms = _binding_mechanisms(document["binding_mechanisms"])
    authority_behavior = _enum_value(
        AuthorityBehavior,
        _required_text(document, "authority_behavior"),
        "authority_behavior",
    )
    version_argument = _optional_text(document, "version_argument")
    effect_category = _optional_text(document, "effect_category")
    safety_oracle = _optional_text(document, "safety_oracle")

    _validate_semantic_constraints(
        operation=operation,
        predicate=predicate,
        binding_mechanisms=binding_mechanisms,
        authority_behavior=authority_behavior,
        version_argument=version_argument,
        effect_category=effect_category,
    )

    return ToolContract(
        contract_id=contract_id,
        operation=operation,
        resource_argument=resource_argument,
        predicate=predicate,
        binding_mechanisms=binding_mechanisms,
        authority_behavior=authority_behavior,
        version_argument=version_argument,
        effect_category=effect_category,
        safety_oracle=safety_oracle,
    )


def _required_text(document: Mapping[str, Any], field_name: str) -> str:
    value = document[field_name]
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError(f"{field_name} must be a non-empty string")
    return value


def _optional_text(document: Mapping[str, Any], field_name: str) -> str | None:
    value = document.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError(f"{field_name} must be null or a non-empty string")
    return value


def _enum_value[EnumValue: StrEnum](
    enum_type: type[EnumValue], value: str, field_name: str
) -> EnumValue:
    try:
        return enum_type(value)
    except ValueError as error:
        raise ContractValidationError(f"{field_name} has unsupported value: {value}") from error


def _binding_mechanisms(value: object) -> tuple[BindingMechanism, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ContractValidationError("binding_mechanisms must be a non-empty list")
    if not value:
        raise ContractValidationError("binding_mechanisms must be a non-empty list")

    bindings = tuple(
        _enum_value(BindingMechanism, item, "binding_mechanisms")
        for item in value
        if isinstance(item, str)
    )
    if len(bindings) != len(value):
        raise ContractValidationError("binding_mechanisms entries must be strings")
    if len(set(bindings)) != len(bindings):
        raise ContractValidationError("binding_mechanisms must not contain duplicates")
    if BindingMechanism.NONE in bindings and len(bindings) > 1:
        raise ContractValidationError("binding_mechanisms cannot combine none with protections")
    return bindings


def _validate_semantic_constraints(
    *,
    operation: ToolOperation,
    predicate: str | None,
    binding_mechanisms: tuple[BindingMechanism, ...],
    authority_behavior: AuthorityBehavior,
    version_argument: str | None,
    effect_category: str | None,
) -> None:
    if operation == ToolOperation.CHECK and predicate is None:
        raise ContractValidationError("check contracts must declare predicate")
    if operation == ToolOperation.EFFECT and effect_category is None:
        raise ContractValidationError("effect contracts must declare effect_category")
    if BindingMechanism.VERSION in binding_mechanisms and version_argument is None:
        raise ContractValidationError("version binding requires version_argument")
    if (
        BindingMechanism.NONE in binding_mechanisms
        and authority_behavior == AuthorityBehavior.ENFORCED
    ):
        raise ContractValidationError("none binding cannot be authority-enforced")
