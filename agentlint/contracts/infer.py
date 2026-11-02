"""Draft contract inference from a tool's name and parameter list.

The heuristics read only what a tool schema exposes (an MCP ``inputSchema`` or an OpenAPI
operation): the tool name, parameter names and which parameters are required. They never
see documentation prose. Fields that need semantic knowledge -- whether a read is a
security-relevant *check* and what it asserts, and whether the resource authority enforces a
binding -- are left for the contract author (``predicate=None``, ``authority=unknown``).
"""

from __future__ import annotations

import re
from typing import Any

_READ = (
    "get",
    "read",
    "list",
    "head",
    "describe",
    "fetch",
    "search",
    "range",
    "query",
    "ls",
    "retrieve",
    "objects_get",
    "kv_get",
)
_CHECK_HINT = ("status", "check", "verify", "validate", "introspect", "info", "properties", "scan")
_EFFECT = (
    "create",
    "update",
    "put",
    "delete",
    "merge",
    "write",
    "edit",
    "patch",
    "replace",
    "apply",
    "move",
    "copy",
    "capture",
    "refund",
    "set",
    "exec",
    "txn",
    "push",
    "post",
    "insert",
    "index",
    "send",
    "deploy",
    "transfer",
    "ack",
)
_VERSION_PARAMS = re.compile(
    r"^(if_?match|ifmatch|etag|sha|blob_sha|version|resource_?version|resourceversion|"
    r"if_?generation_?match|ifgenerationmatch|cas|rev|_rev|if_seq_no|mod_revision|compare|"
    r"expect(ed)?(_\w+)?|preconditions|copysourceifmatch|if_unmodified_since)$",
    re.IGNORECASE,
)
_IDENTITY_PARAMS = re.compile(r"^(versionid|version_id|fd|handle|digest|receipt_handle)$", re.I)
_RESOURCE_PREF = (
    "key",
    "path",
    "id",
    "name",
    "object",
    "blob",
    "ref",
    "pull_number",
    "channel",
    "payment_intent",
    "source",
    "copysource",
    "sql",
)


def _tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[_\W]+", name.lower()) if t]


def infer_contract(name: str, parameters: list[str], required: list[str]) -> dict[str, Any]:
    """Return a draft contract document for a tool."""

    tokens = _tokens(name)
    head = tokens[0] if tokens else ""
    if head in _EFFECT or any(t in _EFFECT for t in tokens[:2]):
        operation = "effect"
    elif any(t in _CHECK_HINT for t in tokens):
        operation = "check"
    elif head in _READ or name.lower() in _READ:
        operation = "read"
    else:
        operation = "read"

    version_arg = next((p for p in parameters if _VERSION_PARAMS.match(p)), None)
    identity_arg = next((p for p in parameters if _IDENTITY_PARAMS.match(p)), None)
    mechanisms: list[str] = ["none"]
    if operation == "effect":
        if version_arg is not None:
            mechanisms = ["version"]
        elif identity_arg is not None:
            mechanisms = ["stable_identity"]

    resource = _resource_argument(parameters, required)
    draft: dict[str, Any] = {
        "operation": operation,
        "resource_argument": resource,
        "predicate": None,
        "binding_mechanisms": mechanisms,
        "authority_behavior": "unknown",
    }
    if mechanisms == ["version"]:
        draft["version_argument"] = version_arg
    return draft


_CONTAINER_ARGS = frozenset(
    ("owner", "repo", "bucket", "namespace", "tablename", "index", "container", "remote")
)


def _resource_argument(parameters: list[str], required: list[str]) -> str:
    candidates = required or parameters
    for pref in _RESOURCE_PREF:
        for p in candidates:
            name = p.lower()
            if name.endswith(pref) and name not in _CONTAINER_ARGS:
                return p
    return candidates[-1] if candidates else ""


INFERRED_FIELDS = (
    "operation",
    "resource_argument",
    "version_argument",
    "binding_mechanisms",
    "authority_behavior",
    "predicate",
)


def field_agreement(draft: dict[str, Any], contract: dict[str, Any]) -> dict[str, bool]:
    """Compare a draft with the hand-written contract field by field."""

    out: dict[str, bool] = {}
    for f in INFERRED_FIELDS:
        a, b = draft.get(f), contract.get(f)
        if f == "binding_mechanisms":
            a, b = sorted(a or []), sorted(b or [])
        out[f] = a == b
    return out
