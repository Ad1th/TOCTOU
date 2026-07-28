"""Tests for M2.3 deterministic finding generation."""

from __future__ import annotations

from agentlint.contracts.models import (
    AuthorityBehavior,
    BindingMechanism,
    ToolContract,
    ToolOperation,
)
from agentlint.ir import (
    BindingReference,
    Edge,
    FindingKind,
    MissingBinding,
    Node,
    NodeKind,
    RepairObligationId,
    ResourceReference,
    ResourceType,
    Workflow,
    generate_findings,
    propagate_dependencies,
)


def test_vulnerable_workflow_generates_missing_binding_finding() -> None:
    """A check-effect dependency without an enforced binding reports one finding."""

    resource = ResourceReference("account:123", "key", ResourceType.KEY_VALUE)
    workflow = Workflow(
        workflow_id="vulnerable",
        nodes=(
            Node(
                node_id="check",
                kind=NodeKind.TOOL_CALL,
                contract=_check_contract(),
                resources=(resource,),
            ),
            Node(node_id="effect", kind=NodeKind.TOOL_CALL, contract=_effect_contract()),
        ),
        edges=(Edge(edge_id="e1", source_id="check", target_id="effect"),),
    )

    findings = generate_findings(workflow, propagate_dependencies(workflow))

    assert len(findings) == 1
    assert findings[0].kind == FindingKind.MISSING_CHECK_EFFECT_BINDING
    assert findings[0].resource == resource
    assert findings[0].check_node_id == "check"
    assert findings[0].effect_node_id == "effect"
    assert findings[0].missing_binding == MissingBinding.AUTHORITY_ENFORCED_CHECK_EFFECT_BINDING
    assert findings[0].location.workflow_id == "vulnerable"
    assert findings[0].location.node_id == "effect"
    assert findings[0].repair_obligation_id == RepairObligationId.BIND_CHECK_TO_EFFECT


def test_correctly_bound_workflow_has_no_finding() -> None:
    """An authority-enforced binding suppresses the missing-binding finding."""

    resource = ResourceReference("account:123", "key", ResourceType.KEY_VALUE)
    binding = BindingReference(
        mechanism=BindingMechanism.VERSION,
        contract_id="kv_version.debit_with_cas",
        authority_enforced=True,
    )
    workflow = Workflow(
        workflow_id="protected",
        nodes=(
            Node(
                node_id="check",
                kind=NodeKind.TOOL_CALL,
                contract=_check_contract(),
                resources=(resource,),
            ),
            Node(
                node_id="effect",
                kind=NodeKind.TOOL_CALL,
                contract=_effect_contract(),
                bindings=(binding,),
            ),
        ),
        edges=(Edge(edge_id="e1", source_id="check", target_id="effect"),),
    )

    assert generate_findings(workflow, propagate_dependencies(workflow)) == ()


def test_multiple_findings_are_generated_for_multiple_unbound_checks() -> None:
    """Independent unbound check-effect dependencies produce multiple findings."""

    account = ResourceReference("account:123", "key", ResourceType.KEY_VALUE)
    item = ResourceReference("https://service/item/1", "item_url", ResourceType.HTTP)
    workflow = Workflow(
        workflow_id="multiple_findings",
        nodes=(
            Node(
                node_id="check_account",
                kind=NodeKind.TOOL_CALL,
                contract=_check_contract("kv_version.read_balance"),
                resources=(account,),
            ),
            Node(
                node_id="effect_account",
                kind=NodeKind.TOOL_CALL,
                contract=_effect_contract("kv_version.debit_without_cas"),
            ),
            Node(
                node_id="check_item",
                kind=NodeKind.TOOL_CALL,
                contract=_check_contract("http_etag.get_quote"),
                resources=(item,),
            ),
            Node(
                node_id="effect_item",
                kind=NodeKind.TOOL_CALL,
                contract=_effect_contract("http_etag.purchase_without_if_match"),
            ),
        ),
        edges=(
            Edge(edge_id="e1", source_id="check_account", target_id="effect_account"),
            Edge(edge_id="e2", source_id="check_item", target_id="effect_item"),
        ),
    )

    findings = generate_findings(workflow)

    assert [finding.check_node_id for finding in findings] == ["check_account", "check_item"]
    assert [finding.effect_node_id for finding in findings] == ["effect_account", "effect_item"]


def test_finding_order_is_deterministic() -> None:
    """Repeated generation over the same dependency graph returns stable ordering."""

    workflow = Workflow(
        workflow_id="deterministic_findings",
        nodes=(
            Node(
                node_id="check_a",
                kind=NodeKind.TOOL_CALL,
                contract=_check_contract("check.a"),
                resources=(ResourceReference("r:a", "resource"),),
            ),
            Node(
                node_id="check_b",
                kind=NodeKind.TOOL_CALL,
                contract=_check_contract("check.b"),
                resources=(ResourceReference("r:b", "resource"),),
            ),
            Node(node_id="effect", kind=NodeKind.TOOL_CALL, contract=_effect_contract()),
        ),
        edges=(
            Edge(edge_id="e1", source_id="check_a", target_id="effect"),
            Edge(edge_id="e2", source_id="check_b", target_id="effect"),
        ),
    )

    first = generate_findings(workflow)
    second = generate_findings(workflow)

    assert first == second
    assert [finding.resource.resource_id for finding in first] == ["r:a", "r:b"]


def test_no_false_finding_when_only_read_reaches_effect() -> None:
    """Only CHECK to EFFECT dependency relationships are reported."""

    workflow = Workflow(
        workflow_id="read_to_effect",
        nodes=(
            Node(
                node_id="read",
                kind=NodeKind.TOOL_CALL,
                contract=ToolContract(
                    contract_id="file.read",
                    operation=ToolOperation.READ,
                    resource_argument="path",
                    predicate=None,
                    binding_mechanisms=(BindingMechanism.NONE,),
                    authority_behavior=AuthorityBehavior.UNKNOWN,
                ),
                resources=(ResourceReference("file:/tmp/a", "path"),),
            ),
            Node(node_id="effect", kind=NodeKind.TOOL_CALL, contract=_effect_contract()),
        ),
        edges=(Edge(edge_id="e1", source_id="read", target_id="effect"),),
    )

    assert generate_findings(workflow) == ()


def _check_contract(contract_id: str = "kv_version.read_balance") -> ToolContract:
    return ToolContract(
        contract_id=contract_id,
        operation=ToolOperation.CHECK,
        resource_argument="key",
        predicate="balance_sufficient",
        binding_mechanisms=(BindingMechanism.NONE,),
        authority_behavior=AuthorityBehavior.UNKNOWN,
    )


def _effect_contract(contract_id: str = "kv_version.debit_without_cas") -> ToolContract:
    return ToolContract(
        contract_id=contract_id,
        operation=ToolOperation.EFFECT,
        resource_argument="key",
        predicate=None,
        binding_mechanisms=(BindingMechanism.NONE,),
        authority_behavior=AuthorityBehavior.UNKNOWN,
        effect_category="debit",
        safety_oracle="no_overdraft",
    )
