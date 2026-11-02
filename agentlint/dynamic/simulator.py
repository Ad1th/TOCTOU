"""Dynamic check-effect violation detection by executing workflow IR under schedules.

This module shares no analysis code with the static rule. It *executes* a workflow:

* a run walks one path from the start node; at a node with several successors it picks one
  (uniformly in random mode, exhaustively in systematic mode); loops are bounded;
* every resource has a version; a ``check`` node records the version it observed;
* an *adversary* may mutate a resource between two steps (a concurrent writer);
* an ``effect`` node on a resource whose version changed since it was last checked is a
  stale effect. The simulated resource authority rejects it if the call site passed a
  binding that the authority enforces (per the tool contract); otherwise the effect is
  applied and a **violation** is recorded.

``random_testing`` models schedule fuzzing (each run: random path, each step boundary
mutates a previously checked resource with probability ``p``). ``systematic_testing``
enumerates every path up to a bound and, on each, every single-mutation schedule
(one mutation of one checked resource at one step boundary); it is complete for
one-mutation witnesses on the explored paths but its cost grows with paths x steps.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from agentlint.contracts.models import AuthorityBehavior, BindingMechanism, ToolOperation
from agentlint.ir.models import Node, ResourceReference, Workflow


@dataclass(frozen=True, slots=True)
class RunResult:
    violations: tuple[tuple[str, str], ...]  # (effect node, resource key)
    rejected: int
    steps: int


def _key(r: ResourceReference) -> str:
    return r.key


def _authority_rejects(node: Node, key: str) -> bool:
    c = node.contract
    if c is None or c.authority_behavior != AuthorityBehavior.ENFORCED:
        return False
    for b in node.bindings:
        if (
            b.mechanism != BindingMechanism.NONE
            and b.authority_enforced
            and b.mechanism in c.binding_mechanisms
            and (b.resource_id is None or b.resource_id == key)
        ):
            return True
    return False


def _start(workflow: Workflow) -> str:
    targets = {e.target_id for e in workflow.edges}
    for n in workflow.nodes:
        if n.node_id not in targets:
            return n.node_id
    return workflow.nodes[0].node_id


def execute(workflow: Workflow, path: list[str], mutations: set[tuple[int, str]]) -> RunResult:
    """Execute ``path``; ``mutations`` holds (step index, resource key) adversary writes,
    applied just before the step with that index."""

    by_id = {n.node_id: n for n in workflow.nodes}
    version: dict[str, int] = {}
    checked: dict[str, int] = {}
    violations: list[tuple[str, str]] = []
    rejected = 0
    for step, node_id in enumerate(path):
        for s, key in mutations:
            if s == step:
                version[key] = version.get(key, 0) + 1
        node = by_id[node_id]
        op = node.contract.operation if node.contract is not None else None
        if op == ToolOperation.CHECK:
            for r in node.resources:
                checked[_key(r)] = version.get(_key(r), 0)
        elif op == ToolOperation.EFFECT:
            stale = [
                _key(r)
                for r in node.resources
                if _key(r) in checked and version.get(_key(r), 0) != checked[_key(r)]
            ]
            if any(_authority_rejects(node, k) for k in stale):
                rejected += 1
                continue
            for k in stale:
                violations.append((node_id, k))
            for r in node.resources:
                version[_key(r)] = version.get(_key(r), 0) + 1
                checked.pop(_key(r), None)
    return RunResult(tuple(violations), rejected, len(path))


def _successors(workflow: Workflow) -> dict[str, list[str]]:
    succ: dict[str, list[str]] = {n.node_id: [] for n in workflow.nodes}
    for e in workflow.edges:
        succ[e.source_id].append(e.target_id)
    return succ


def random_path(workflow: Workflow, rng: random.Random, max_visits: int = 3) -> list[str]:
    succ = _successors(workflow)
    visits: dict[str, int] = {}
    cur = _start(workflow)
    path = []
    while True:
        visits[cur] = visits.get(cur, 0) + 1
        path.append(cur)
        options = [s for s in succ[cur] if visits.get(s, 0) < max_visits]
        if not options:
            return path
        cur = rng.choice(options)


def all_paths(workflow: Workflow, max_visits: int = 2, limit: int = 20000) -> list[list[str]]:
    succ = _successors(workflow)
    out: list[list[str]] = []
    stack: list[tuple[str, list[str], dict[str, int]]] = [(_start(workflow), [], {})]
    while stack and len(out) < limit:
        node, path, visits = stack.pop()
        visits = dict(visits)
        visits[node] = visits.get(node, 0) + 1
        path = path + [node]
        options = [s for s in succ[node] if visits.get(s, 0) < max_visits]
        if not options:
            out.append(path)
            continue
        for s in reversed(options):
            stack.append((s, path, visits))
    return out


def _checked_keys_before(workflow: Workflow, path: list[str]) -> list[tuple[int, str]]:
    by_id = {n.node_id: n for n in workflow.nodes}
    seen: list[str] = []
    points: list[tuple[int, str]] = []
    for step, node_id in enumerate(path):
        for k in seen:
            points.append((step, k))
        node = by_id[node_id]
        if node.contract is not None and node.contract.operation == ToolOperation.CHECK:
            for r in node.resources:
                if _key(r) not in seen:
                    seen.append(_key(r))
    return points


@dataclass(frozen=True, slots=True)
class DynamicVerdict:
    detected: bool
    executions: int
    first_witness_at: int | None


def random_testing(workflow: Workflow, budget: int, p: float, seed: int) -> DynamicVerdict:
    rng = random.Random(seed)
    for i in range(1, budget + 1):
        path = random_path(workflow, rng)
        points = _checked_keys_before(workflow, path)
        mutations = {pt for pt in points if rng.random() < p}
        if execute(workflow, path, mutations).violations:
            return DynamicVerdict(True, i, i)
    return DynamicVerdict(False, budget, None)


def systematic_testing(workflow: Workflow, max_visits: int = 2) -> DynamicVerdict:
    executions = 0
    for path in all_paths(workflow, max_visits=max_visits):
        for point in _checked_keys_before(workflow, path):
            executions += 1
            if execute(workflow, path, {point}).violations:
                return DynamicVerdict(True, executions, executions)
    return DynamicVerdict(False, executions, None)
