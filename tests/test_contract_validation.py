"""Tests for M1 tool-contract validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentlint.contracts import (
    BindingMechanism,
    ContractValidationError,
    ToolOperation,
    load_contract,
    validate_contract,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_all_pilot_contracts_validate() -> None:
    """Every M1 pilot contract fixture conforms to the contract schema."""

    contracts = [
        load_contract(contract_path)
        for contract_path in sorted((PROJECT_ROOT / "benchmark/pilot/contracts").glob("*.json"))
    ]

    assert len(contracts) == 36
    assert {contract.operation for contract in contracts} == {
        ToolOperation.CHECK,
        ToolOperation.EFFECT,
    }
    assert any(BindingMechanism.VERSION in contract.binding_mechanisms for contract in contracts)


@pytest.mark.parametrize(
    "malformed_contract",
    [
        {},
        {
            "schema_version": 1,
            "contract_id": "bad.missing_resource",
            "operation": "check",
            "binding_mechanisms": ["none"],
            "authority_behavior": "unknown",
        },
        {
            "schema_version": 1,
            "contract_id": "bad.check_without_predicate",
            "operation": "check",
            "resource_argument": "path",
            "binding_mechanisms": ["none"],
            "authority_behavior": "unknown",
        },
        {
            "schema_version": 1,
            "contract_id": "bad.version_without_argument",
            "operation": "effect",
            "resource_argument": "key",
            "binding_mechanisms": ["version"],
            "authority_behavior": "enforced",
            "effect_category": "debit",
        },
        {
            "schema_version": 1,
            "contract_id": "bad.none_enforced",
            "operation": "effect",
            "resource_argument": "key",
            "binding_mechanisms": ["none"],
            "authority_behavior": "enforced",
            "effect_category": "debit",
        },
    ],
)
def test_validator_rejects_malformed_contracts(malformed_contract: dict[str, object]) -> None:
    """M1 acceptance requires malformed contracts to be rejected."""

    with pytest.raises(ContractValidationError):
        validate_contract(malformed_contract)
