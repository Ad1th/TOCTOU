"""Synthetic workflow generator for scalability and differential testing."""

from __future__ import annotations

import random

from agentlint.contracts.models import (
    AuthorityBehavior,
    BindingMechanism,
    ToolContract,
    ToolOperation,
)
from agentlint.ir.models import BindingReference, Edge, Node, NodeKind, ResourceReference, Workflow

CHECK = ToolContract(
    "syn.check",
    ToolOperation.CHECK,
    "res",
    "p",
    (BindingMechanism.NONE,),
    AuthorityBehavior.UNKNOWN,
)
EFFECT = ToolContract(
    "syn.effect",
    ToolOperation.EFFECT,
    "res",
    None,
    (BindingMechanism.NONE,),
    AuthorityBehavior.UNKNOWN,
    effect_category="w",
    safety_oracle="o",
)
BOUND = ToolContract(
    "syn.effect_bound",
    ToolOperation.EFFECT,
    "res",
    None,
    (BindingMechanism.VERSION,),
    AuthorityBehavior.ENFORCED,
    version_argument="v",
    effect_category="w",
    safety_oracle="o",
)
READ = ToolContract(
    "syn.read", ToolOperation.READ, "res", None, (BindingMechanism.NONE,), AuthorityBehavior.UNKNOWN
)
TOPOLOGIES = ("chain", "layered", "random_dag", "cyclic")


def synthetic_edges(topology: str, n: int, rng: random.Random) -> list[tuple[int, int]]:
    if topology == "chain":
        return [(i, i + 1) for i in range(n - 1)]
    if topology in ("layered", "cyclic"):
        width = max(2, int(n**0.5) // 2)
        layers = [list(range(i, min(i + width, n))) for i in range(0, n, width)]
        edges = set()
        for a, b in zip(layers, layers[1:], strict=False):
            for u in a:
                for v in rng.sample(b, k=min(2, len(b))):
                    edges.add((u, v))
            for v in b:  # keep every node reachable
                edges.add((rng.choice(a), v))
        if topology == "cyclic":
            for _ in range(max(1, n // 20)):
                i = rng.randrange(1, len(layers))
                edges.add((rng.choice(layers[i]), rng.choice(layers[rng.randrange(0, i)])))
        return sorted(edges)
    # random_dag: each node links to 3 random later nodes inside a window of 100
    edges = set()
    for i in range(n - 1):
        for _ in range(3):
            edges.add((i, rng.randint(i + 1, min(n - 1, i + 100))))
        edges.add((i, i + 1))
    return sorted(edges)


def synthetic_workflow(
    topology: str, n: int, seed: int, pool: int | None = None, window_resources: bool = True
) -> Workflow:
    """A workflow with 30% checks, 30% effects (half bound), 1-2 resources per tool node.

    With ``window_resources`` each node draws resources from a pool local to its position
    (workflows touch resources in segments); otherwise from one global pool of ``pool``.
    """

    rng = random.Random(seed)
    pool = pool or max(10, n // 20)
    nodes = []
    for i in range(n):
        role = rng.random()
        base = (i * pool) // n if window_resources else 0
        span = 5 if window_resources else pool
        res = tuple(
            ResourceReference(f"r{base + rng.randrange(span)}", "res")
            for _ in range(rng.randint(1, 2))
        )
        res = tuple(dict.fromkeys(res))
        if role < 0.3:
            nodes.append(Node(f"n{i}", NodeKind.TOOL_CALL, contract=CHECK, resources=res))
        elif role < 0.6:
            if rng.random() < 0.5:
                nodes.append(
                    Node(
                        f"n{i}",
                        NodeKind.TOOL_CALL,
                        contract=BOUND,
                        resources=res,
                        bindings=(
                            BindingReference(BindingMechanism.VERSION, "syn.effect_bound", True),
                        ),
                    )
                )
            else:
                nodes.append(Node(f"n{i}", NodeKind.TOOL_CALL, contract=EFFECT, resources=res))
        elif role < 0.8:
            nodes.append(Node(f"n{i}", NodeKind.TOOL_CALL, contract=READ, resources=res))
        else:
            nodes.append(Node(f"n{i}", NodeKind.COMPUTE))
    edges = tuple(
        Edge(f"e{k}", f"n{a}", f"n{b}")
        for k, (a, b) in enumerate(synthetic_edges(topology, n, rng))
    )
    return Workflow(f"{topology}_{n}_{seed}", tuple(nodes), edges)
