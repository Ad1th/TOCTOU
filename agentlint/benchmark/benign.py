"""Seeded generator for realistic benign (and injected-risk) workflows over real tool contracts.

Workflows are composed from *segments*. Each segment uses its own resource identity, so
segments never share state. Every benign segment belongs to one of eight patterns that have
no unprotected check-effect dependency by definition of the property:

  P1 read-only            reads only, no effects
  P2 effect-only          effects with no prior check of that resource
  P3 check-then-read      a check followed only by reads of the same resource
  P4 unrelated-effect     check of resource A, unbound effect on a different resource B
  P5 bound-effect         check followed by an effect whose call site passes an
                          authority-enforced binding (CAS token, precondition, revalidation)
  P6 exclusive-branch     check and unbound effect on mutually exclusive branches
  P7 effect-then-check    an effect followed by a later (audit) check
  P8 bound-agent-loop     a ReAct-style loop whose effects are all bound

An *injected-risk* workflow is a benign workflow into which exactly one risky segment is
spliced: a check followed by an unbound or advisory effect on the same resource.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentlint.benchmark.tool_catalog import CATALOG

PATTERNS = ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8")
PATTERN_NAMES = {
    "P1": "Read-only pipeline",
    "P2": "Effect without prior check",
    "P3": "Check then read",
    "P4": "Check A, effect on B",
    "P5": "Authority-bound effect",
    "P6": "Exclusive branches",
    "P7": "Effect then audit check",
    "P8": "Bound agent loop",
}

# (check tool, bound effect tool) on the same service and resource argument
BOUND_PAIRS = (
    ("github.get_pull_request_status", "github.merge_pull_request"),
    ("k8s.get_deployment", "k8s.replace_deployment"),
    ("k8s.get_deployment", "k8s.delete_deployment"),
    ("s3.head_object", "s3.put_object"),
    ("s3.head_object", "s3.delete_object"),
    ("ddb.get_item", "ddb.update_item"),
    ("gcs.objects_get", "gcs.objects_insert"),
    ("gcs.objects_get", "gcs.objects_delete"),
    ("stripe.retrieve_payment_intent", "stripe.capture_payment_intent"),
    ("stripe.retrieve_payment_intent", "stripe.create_refund"),
    ("redis.get", "redis.exec_watched"),
    ("etcd.range", "etcd.txn"),
    ("consul.kv_get", "consul.kv_put"),
    ("es.get_doc", "es.index_doc"),
    ("azure.get_blob_properties", "azure.put_blob"),
)
# (check tool, effect tool with no usable binding on that call) -- used for risky injections
RISKY_PAIRS = (
    ("fs.get_file_info", "fs.write_file"),
    ("fs.get_file_info", "fs.edit_file"),
    ("k8s.get_deployment", "k8s.patch_deployment"),
    ("redis.get", "redis.set"),
    ("etcd.range", "etcd.put"),
    ("git.ls_remote", "git.push_force_with_lease"),
    ("fs.get_file_info", "posix.flock_write"),
    # binding-capable tools called without passing the binding argument
    ("github.get_pull_request_status", "github.merge_pull_request"),
    ("s3.head_object", "s3.put_object"),
    ("consul.kv_get", "consul.kv_put"),
    ("es.get_doc", "es.index_doc"),
)
READS = (
    "github.get_pull_request",
    "github.get_file_contents",
    "fs.read_file",
    "fs.list_directory",
    "s3.get_object",
    "pg.query",
)
UNBOUND_EFFECTS = (
    "fs.write_file",
    "fs.edit_file",
    "fs.move_file",
    "k8s.patch_deployment",
    "redis.set",
    "etcd.put",
    "slack.chat_post_message",
    "github.merge_pull_request",
    "s3.put_object",
)
CHECKS = tuple(
    t["contract"]["contract_id"] for t in CATALOG if t["contract"]["operation"] == "check"
)

_BY_ID = {t["contract"]["contract_id"]: t for t in CATALOG}
_RTYPE = {
    "github": "git",
    "fs": "file",
    "k8s": "cluster",
    "s3": "cloud_object",
    "ddb": "key_value",
    "gcs": "cloud_object",
    "stripe": "payment",
    "redis": "key_value",
    "etcd": "key_value",
    "consul": "key_value",
    "es": "database",
    "azure": "cloud_object",
    "slack": "channel",
    "git": "git",
    "pg": "database",
    "posix": "file",
}


@dataclass
class _Builder:
    workflow_id: str
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[tuple[str, str]] = field(default_factory=list)
    counter: int = 0

    def add(
        self,
        kind: str,
        contract: str | None = None,
        resource: str | None = None,
        bound: bool = False,
    ) -> str:
        self.counter += 1
        node_id = f"n{self.counter}"
        node: dict[str, Any] = {"node_id": node_id, "kind": kind}
        if contract is not None:
            node["contract_id"] = contract
            tool = _BY_ID[contract]
            service = tool["service"]
            if resource is not None:
                node["resources"] = [
                    {
                        "resource_id": resource,
                        "argument_name": tool["contract"]["resource_argument"],
                        "resource_type": _RTYPE[service],
                    }
                ]
            if bound:
                mech = tool["contract"]["binding_mechanisms"][0]
                node["bindings"] = [
                    {"mechanism": mech, "contract_id": contract, "authority_enforced": True}
                ]
        self.nodes.append(node)
        return node_id

    def edge(self, a: str, b: str) -> None:
        self.edges.append((a, b))

    def document(self, family: str, variant: str, meta: dict[str, Any]) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "family_id": family,
            "variant": variant,
            "meta": meta,
            "nodes": self.nodes,
            "edges": [
                {"edge_id": f"e{i + 1}", "source_id": s, "target_id": t}
                for i, (s, t) in enumerate(self.edges)
            ],
        }


def _res(contract: str, tag: str) -> str:
    tool = _BY_ID[contract]
    return f"{tool['service']}:{tool['contract']['resource_argument']}:{tag}"


def _segment(b: _Builder, rng: random.Random, pattern: str, entry: str, tag: str) -> str:
    """Append one segment after ``entry`` and return its exit node id."""

    def seq(*specs: tuple[str, str | None, str | None, bool]) -> str:
        cur = entry
        for kind, contract, resource, bound in specs:
            nid = b.add(kind, contract, resource, bound)
            b.edge(cur, nid)
            cur = nid
        return cur

    if pattern == "P1":
        reads = rng.sample(READS, k=rng.randint(2, 4))
        return seq(
            *[("tool_call", r, _res(r, tag), False) for r in reads], ("compute", None, None, False)
        )
    if pattern == "P2":
        effs = rng.sample(UNBOUND_EFFECTS, k=rng.randint(1, 3))
        return seq(*[("tool_call", e, _res(e, f"{tag}{i}"), False) for i, e in enumerate(effs)])
    if pattern == "P3":
        check = rng.choice(CHECKS)
        rid = _res(check, tag)
        return seq(
            ("tool_call", check, rid, False),
            ("compute", None, None, False),
            (
                "tool_call",
                "fs.read_file" if check.startswith("fs") else rng.choice(READS),
                rid,
                False,
            ),
        )
    if pattern == "P4":
        check, eff = rng.choice(CHECKS), rng.choice(UNBOUND_EFFECTS)
        return seq(
            ("tool_call", check, _res(check, tag), False),
            ("decision", None, None, False),
            ("tool_call", eff, _res(eff, tag + "other"), False),
        )
    if pattern == "P5":
        check, eff = rng.choice(BOUND_PAIRS)
        rid = _res(check, tag)
        return seq(
            ("tool_call", check, rid, False),
            ("compute", None, None, False),
            ("tool_call", eff, rid, True),
        )
    if pattern == "P6":
        check, eff = rng.choice(RISKY_PAIRS)
        rid = _res(check, tag)
        route = b.add("decision")
        b.edge(entry, route)
        c = b.add("tool_call", check, rid)
        e = b.add("tool_call", eff, rid)
        join = b.add("compute")
        for a, z in ((route, c), (route, e), (c, join), (e, join)):
            b.edge(a, z)
        return join
    if pattern == "P7":
        check, eff = rng.choice(RISKY_PAIRS)
        rid = _res(check, tag)
        return seq(
            ("tool_call", eff, rid, False),
            ("compute", None, None, False),
            ("tool_call", check, rid, False),
        )
    # P8: bound agent loop
    agent = b.add("decision")
    b.edge(entry, agent)
    for _ in range(rng.randint(1, 3)):
        check, eff = rng.choice(BOUND_PAIRS)
        rid = _res(check, tag + str(b.counter))
        c = b.add("tool_call", check, rid)
        e = b.add("tool_call", eff, rid, True)
        for a, z in ((agent, c), (c, agent), (agent, e), (e, agent)):
            b.edge(a, z)
    done = b.add("compute")
    b.edge(agent, done)
    return done


def _risky_segment(b: _Builder, rng: random.Random, entry: str, tag: str) -> tuple[str, str]:
    check, eff = rng.choice(RISKY_PAIRS)
    rid = _res(check, tag)
    c = b.add("tool_call", check, rid)
    m = b.add("compute")
    # an advisory tool is called *with* its binding argument: the author believes it is safe
    advisory = _BY_ID[eff]["contract"]["authority_behavior"] == "advisory"
    e = b.add("tool_call", eff, rid, bound=advisory)
    b.edge(entry, c)
    b.edge(c, m)
    b.edge(m, e)
    return e, f"{check}->{eff}"


def generate(
    seed: int = 20261101, n_benign: int = 400, n_injected: int = 100
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    docs: list[dict[str, Any]] = []
    for i in range(n_benign + n_injected):
        injected = i >= n_benign
        b = _Builder(workflow_id=f"{'inj' if injected else 'benign'}_{i:04d}")
        cur = b.add("start")
        k = rng.randint(1, 6)
        patterns = [rng.choice(PATTERNS) for _ in range(k)]
        insert_at = rng.randint(0, k) if injected else -1
        risky = None
        for j, pattern in enumerate(patterns + ["__end__"]):
            if j == insert_at:
                cur, risky = _risky_segment(b, rng, cur, f"w{i}s{j}risk")
            if pattern == "__end__":
                break
            cur = _segment(b, rng, pattern, cur, f"w{i}s{j}")
        end = b.add("end")
        b.edge(cur, end)
        meta = {"patterns": patterns, "risky_pair": risky}
        docs.append(
            b.document(
                "benign_mix" if not injected else "injected_mix",
                "vulnerable" if injected else "benign",
                meta,
            )
        )
    return docs


def write(out_dir: Path, **kwargs: Any) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    docs = generate(**kwargs)
    (out_dir / "benign_workflows.json").write_text(
        json.dumps({"schema_version": 1, "workflows": docs}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return len(docs)


def generate_single_pattern(pattern: str, n: int = 50, seed: int = 7) -> list[dict[str, Any]]:
    """Workflows containing exactly one segment of ``pattern`` (for per-pattern attribution)."""

    rng = random.Random(f"{seed}-{pattern}")
    docs = []
    for i in range(n):
        b = _Builder(workflow_id=f"single_{pattern}_{i:03d}")
        cur = _segment(b, rng, pattern, b.add("start"), f"{pattern}{i}")
        b.edge(cur, b.add("end"))
        docs.append(
            b.document(f"single_{pattern}", "benign", {"patterns": [pattern], "risky_pair": None})
        )
    return docs
