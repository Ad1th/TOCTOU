"""LangGraph / LangChain frontends that build AgentLint workflow IR.

Two independent paths are provided.

``workflow_from_state_graph`` (static)
    Reads a LangGraph ``StateGraph`` without running it. Control flow comes from the
    compiled graph (``get_graph()``), including conditional edges. Tool calls come from
    the AST of each node function: a call ``tool.invoke({...})`` or ``tool({...})`` /
    ``tool(arg=...)`` whose callee name is in the contract registry becomes a tool-call node.
    The resource is the source text of the argument bound to the contract's
    ``resource_argument`` (e.g. ``state['pr']``), so two calls touching the same state
    expression share a resource. A ``version`` binding is recorded when the contract's
    ``version_argument`` is passed and is not the literal ``None``.

``workflow_from_messages`` (trace)
    Converts an executed LangChain message history -- the ``tool_calls`` of each
    ``AIMessage`` -- into a linear workflow whose resources are the concrete argument
    values the agent passed.

For both, a tool whose binding mechanism is intrinsic to the call (``atomic``,
``revalidation``, ``synchronization``, ``stable_identity``) is bound whenever its contract
says the authority enforces it; a ``version`` binding additionally requires the caller to
pass the version argument.
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from agentlint.contracts.models import BindingMechanism, ToolContract
from agentlint.ir.models import (
    BindingReference,
    Edge,
    Node,
    NodeKind,
    ResourceReference,
    Workflow,
)


@dataclass(frozen=True, slots=True)
class ToolCall:
    """A tool invocation recovered from source or from a trace."""

    tool: str
    resource: str | None
    passed: frozenset[str]
    version_is_none: bool = False


def _binding_for(contract: ToolContract, call: ToolCall) -> tuple[BindingReference, ...]:
    mechs = [m for m in contract.binding_mechanisms if m != BindingMechanism.NONE]
    if not mechs:
        return ()
    mech = mechs[0]
    if mech == BindingMechanism.VERSION:
        arg = contract.version_argument
        if arg is None or arg not in call.passed or call.version_is_none:
            return ()
    return (
        BindingReference(
            mechanism=mech,
            contract_id=contract.contract_id,
            # the call site supplies the binding; whether the authority actually enforces it
            # is decided by the contract during finding generation
            authority_enforced=True,
        ),
    )


def _tool_node(node_id: str, contract: ToolContract, call: ToolCall, origin: str) -> Node:
    resources: tuple[ResourceReference, ...] = ()
    if call.resource is not None:
        resources = (
            ResourceReference(resource_id=call.resource, argument_name=contract.resource_argument),
        )
    return Node(
        node_id=node_id,
        kind=NodeKind.TOOL_CALL,
        label=call.tool,
        contract=contract,
        resources=resources,
        bindings=_binding_for(contract, call),
        provenance=(origin,),
    )


# ---------------------------------------------------------------- trace frontend


def workflow_from_messages(
    workflow_id: str,
    messages: Iterable[Any],
    registry: Mapping[str, ToolContract],
) -> Workflow:
    """Build a linear workflow from the tool calls in a LangChain message history."""

    nodes: list[Node] = [Node(node_id="start", kind=NodeKind.START)]
    for message in messages:
        for i, tc in enumerate(getattr(message, "tool_calls", None) or ()):
            name, args = tc["name"], dict(tc.get("args") or {})
            contract = registry.get(name)
            node_id = f"call{len(nodes)}_{i}"
            if contract is None:
                nodes.append(
                    Node(node_id=node_id, kind=NodeKind.UNKNOWN, label=name, provenance=("trace",))
                )
                continue
            value = args.get(contract.resource_argument)
            call = ToolCall(
                tool=name,
                resource=None if value is None else f"{contract.resource_argument}={value}",
                passed=frozenset(k for k, v in args.items() if v is not None),
                version_is_none=contract.version_argument is not None
                and args.get(contract.version_argument) is None,
            )
            nodes.append(_tool_node(node_id, contract, call, f"trace:{tc.get('id', '')}"))
    nodes.append(Node(node_id="end", kind=NodeKind.END))
    edges = tuple(
        Edge(edge_id=f"e{i}", source_id=a.node_id, target_id=b.node_id)
        for i, (a, b) in enumerate(zip(nodes, nodes[1:], strict=False))
    )
    return Workflow(workflow_id=workflow_id, nodes=tuple(nodes), edges=edges)


# ---------------------------------------------------------------- static frontend


def extract_tool_calls(func: Any, registry: Mapping[str, ToolContract]) -> list[ToolCall]:
    """Return registry tool calls in a node function, in source order."""

    try:
        source = textwrap.dedent(inspect.getsource(func))
    except (OSError, TypeError):
        return []
    tree = ast.parse(source)
    calls: list[tuple[int, int, ToolCall]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        callee = node.func
        name: str | None = None
        if isinstance(callee, ast.Attribute) and callee.attr in ("invoke", "ainvoke", "run"):
            if isinstance(callee.value, ast.Name):
                name = callee.value.id
        elif isinstance(callee, ast.Name):
            name = callee.id
        if name is None or name not in registry:
            continue
        contract = registry[name]
        kwargs: dict[str, ast.expr] = {}
        if node.args and isinstance(node.args[0], ast.Dict):
            for k, v in zip(node.args[0].keys, node.args[0].values, strict=False):
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    kwargs[k.value] = v
        for kw in node.keywords:
            if kw.arg is not None:
                kwargs[kw.arg] = kw.value
        res_expr = kwargs.get(contract.resource_argument)
        ver_expr = kwargs.get(contract.version_argument) if contract.version_argument else None
        calls.append(
            (
                node.lineno,
                node.col_offset,
                ToolCall(
                    tool=name,
                    resource=ast.unparse(res_expr) if res_expr is not None else None,
                    passed=frozenset(kwargs),
                    version_is_none=isinstance(ver_expr, ast.Constant) and ver_expr.value is None,
                ),
            )
        )
    calls.sort(key=lambda t: (t[0], t[1]))
    return [c for _, _, c in calls]


def workflow_from_state_graph(
    workflow_id: str,
    graph: Any,
    registry: Mapping[str, ToolContract],
) -> Workflow:
    """Build a workflow from an (uncompiled) LangGraph ``StateGraph`` without executing it."""

    drawable = graph.compile().get_graph()
    first: dict[str, str] = {}
    last: dict[str, str] = {}
    nodes: list[Node] = []
    edges: list[Edge] = []

    def link(a: str, b: str) -> None:
        edges.append(Edge(edge_id=f"e{len(edges) + 1}", source_id=a, target_id=b))

    for name in drawable.nodes:
        if name == "__start__":
            nodes.append(Node(node_id="__start__", kind=NodeKind.START))
            first[name] = last[name] = "__start__"
            continue
        if name == "__end__":
            nodes.append(Node(node_id="__end__", kind=NodeKind.END))
            first[name] = last[name] = "__end__"
            continue
        spec = graph.nodes.get(name)
        func = getattr(getattr(spec, "runnable", None), "func", None)
        calls = extract_tool_calls(func, registry) if func is not None else []
        if not calls:
            nodes.append(
                Node(
                    node_id=name,
                    kind=NodeKind.COMPUTE,
                    label=name,
                    provenance=(f"langgraph:{name}",),
                )
            )
            first[name] = last[name] = name
            continue
        ids = []
        for i, call in enumerate(calls):
            nid = name if len(calls) == 1 else f"{name}#{i}"
            nodes.append(_tool_node(nid, registry[call.tool], call, f"langgraph:{name}"))
            ids.append(nid)
        for a, b in zip(ids, ids[1:], strict=False):
            link(a, b)
        first[name], last[name] = ids[0], ids[-1]

    for e in drawable.edges:
        link(last[e.source], first[e.target])
    return Workflow(workflow_id=workflow_id, nodes=tuple(nodes), edges=tuple(edges))
