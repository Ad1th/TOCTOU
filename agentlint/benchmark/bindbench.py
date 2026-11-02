"""BindBench v2: declarative family specification and deterministic corpus generator.

Every family is one row of ``FAMILIES``. The generator expands a row into three tool
contracts (plus optional advisory/read contracts) and three workflow variants:

* ``vulnerable``     -- the effect depends on the checked resource with no effective binding.
  ``vuln_kind`` selects how: ``unbound`` (no binding), ``advisory`` (a binding is passed but
  the resource authority does not enforce it), or ``mis_scoped`` (a multi-resource effect
  binds only one of the checked resources).
* ``repaired``       -- the same workflow with an authority-enforced binding on every
  checked resource the effect consumes.
* ``safe_near_miss`` -- a structurally similar workflow that has *no* check-effect
  dependency. ``near_miss`` selects one of four constructions: ``different_resource``,
  ``exclusive_branch``, ``read_not_check``, ``effect_before_check``.

``shape`` selects the surrounding control structure: ``linear``, ``branch``, ``loop``
(a cyclic agent loop) or ``multi`` (two checked resources, one effect).
The generator involves no sampling: given this table it is a pure function.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class FamilySpec:
    family_id: str
    origin: str  # "pilot" (v1 family, re-expressed) or "extension" (new in v2)
    category: str
    resource_type: str
    resource_argument: str
    resource_id: str
    check_tool: str
    predicate: str
    effect_tool: str
    effect_category: str
    safety_oracle: str
    mechanism: str
    version_argument: str | None
    vuln_kind: str
    near_miss: str
    shape: str
    grounding: str
    mutation: str


def _f(*row: Any) -> FamilySpec:
    return FamilySpec(*row)


# fmt: off
FAMILIES: tuple[FamilySpec, ...] = (
    # ---- 24 pilot families (v1), re-expressed with explicit effect resources -------------
    _f("async_job_join", "pilot", "Workflow control", "workflow", "job_id", "job:8812",
       "get_job_status", "job_completed", "fetch_results", "job_fetch", "no_partial_results",
       "synchronization", None, "unbound", "read_not_check", "branch",
       "Job APIs exposing a completion barrier (join/await) on result retrieval",
       "job is re-queued after the status check"),
    _f("auth_recheck", "pilot", "Authorization", "authority", "principal_resource",
       "acl:alice:report", "check_permission", "permission_granted", "export_report",
       "data_export", "no_export_without_permission", "revalidation", None, "unbound",
       "different_resource", "linear",
       "Policy enforcement point re-evaluates the decision at use time (PDP/PEP split)",
       "permission revoked after the check"),
    _f("availability", "pilot", "Value / availability", "key_value", "sku", "sku:A-100",
       "check_stock", "stock_available", "reserve_item", "reservation", "no_oversell",
       "atomic", None, "unbound", "exclusive_branch", "branch",
       "Atomic decrement-if-positive reservation primitive",
       "concurrent order consumes the last unit"),
    _f("cloud_generation", "pilot", "Cloud object generation", "cloud_object", "object_name",
       "gs://cfg/app.json", "get_object_metadata", "object_is_expected", "delete_object",
       "deletion", "deletes_only_checked_generation", "version", "if_generation_match",
       "unbound", "effect_before_check", "linear",
       "Google Cloud Storage ifGenerationMatch precondition",
       "object overwritten with a new generation"),
    _f("db_row_version", "pilot", "Database row version", "database", "row_id", "orders:5512",
       "get_order_status", "status_pending", "update_order", "row_update",
       "updates_only_pending_rows", "version", "expected_row_version", "advisory",
       "different_resource", "linear",
       "Optimistic locking with a version column; advisory when the ORM omits it from WHERE",
       "order shipped by another worker"),
    _f("dynamodb_conditional", "pilot", "Versioned key-value state", "key_value", "item_pk",
       "user#77", "get_item", "quota_remaining", "update_item", "conditional_update",
       "never_exceeds_quota", "version", "version", "unbound", "read_not_check", "loop",
       "DynamoDB ConditionExpression on a version attribute", "quota consumed concurrently"),
    _f("file_identity", "pilot", "File / object identity", "file", "path",
       "/srv/uploads/report.csv", "check_path_allowed", "path_allowed", "write_file",
       "file_write", "writes_only_checked_object", "stable_identity", None, "unbound",
       "exclusive_branch", "branch", "openat/fd-based I/O on the checked object",
       "path replaced after the check"),
    _f("git_commit_hash", "pilot", "Git commit hash validation", "git", "ref_name",
       "refs/heads/release", "review_ref", "ref_approved", "deploy_ref", "deployment",
       "deploys_only_reviewed_commit", "stable_identity", None, "unbound",
       "different_resource", "linear", "Deploy by reviewed commit SHA rather than mutable ref",
       "branch force-pushed after review"),
    _f("graphql_mutation_token", "pilot", "HTTP-like resources", "http", "order_node",
       "gql:Order/991", "inspect_order", "order_editable", "mutate_order", "mutation",
       "mutates_only_editable_orders", "version", "version", "advisory", "exclusive_branch",
       "branch", "GraphQL concurrency-token argument; advisory when the resolver ignores it",
       "order locked by fulfilment"),
    _f("http_etag", "pilot", "HTTP-like resources", "http", "item_url",
       "https://shop.example/items/42", "get_quote", "price_acceptable", "purchase",
       "purchase", "pays_checked_price", "version", "if_match", "unbound",
       "effect_before_check", "linear", "HTTP If-Match with ETag (RFC 9110, Sec. 13.1.1)",
       "price updated after the quote"),
    _f("inventory_price_lock", "pilot", "Value / availability", "key_value", "cart_item",
       "cart:31:item:7", "check_price", "price_within_budget", "checkout", "purchase",
       "charges_checked_price", "atomic", None, "unbound", "read_not_check", "linear",
       "Price lock held through checkout", "price changes between check and checkout"),
    _f("k8s_resource_version", "pilot", "Kubernetes resourceVersion", "cluster",
       "deployment_name", "apps/v1/deploy/web", "get_deployment", "replicas_safe",
       "replace_deployment", "update", "no_lost_update", "version", "resource_version",
       "unbound", "different_resource", "loop",
       "Kubernetes metadata.resourceVersion optimistic concurrency",
       "controller scales the deployment"),
    _f("kv_version", "pilot", "Versioned key-value state", "key_value", "key", "account:123",
       "read_balance", "balance_sufficient", "debit", "debit", "no_overdraft", "version",
       "expected_version", "unbound", "exclusive_branch", "linear",
       "Compare-and-swap on a version counter", "balance decreased by another debit"),
    _f("payment_revalidation", "pilot", "Payment authorization revalidation", "payment",
       "payment_id", "pi_3Nx", "authorize_payment", "authorization_valid", "capture_payment",
       "capture", "captures_only_valid_authorization", "revalidation", None, "advisory",
       "effect_before_check", "linear",
       "Processor-side authorization re-check at capture; advisory when cached client-side",
       "authorization voided before capture"),
    _f("queue_ack", "pilot", "Message queue acknowledgement", "queue", "message_id",
       "sqs://jobs/msg-17", "inspect_message", "message_valid", "ack_message",
       "acknowledgement", "acks_only_inspected_delivery", "stable_identity", None, "unbound",
       "read_not_check", "branch", "SQS receipt handle tied to a single receive",
       "visibility timeout expires and message is redelivered"),
    _f("rate_limit_lease", "pilot", "Value / availability", "key_value", "bucket_id",
       "ratelimit:tenant9", "check_tokens", "token_available", "consume_token",
       "consumption", "never_exceeds_limit", "atomic", None, "unbound", "different_resource",
       "loop", "Atomic token-bucket decrement", "tokens consumed concurrently"),
    _f("rbac_role_recheck", "pilot", "Authorization", "authority", "user_role", "rbac:bob",
       "get_role", "role_is_admin", "delete_project", "privileged_action",
       "acts_only_with_role", "revalidation", None, "unbound", "exclusive_branch", "branch",
       "Role re-evaluated by the authorization service at the privileged call",
       "role revoked after the check"),
    _f("redis_watch_multi", "pilot", "Versioned key-value state", "key_value", "redis_key",
       "redis:seat:12A", "get_seat", "seat_free", "book_seat", "booking", "no_double_booking",
       "atomic", None, "unbound", "effect_before_check", "linear",
       "Redis WATCH/MULTI/EXEC optimistic transaction", "seat booked concurrently"),
    _f("rest_if_unmodified", "pilot", "HTTP-like resources", "http", "api_endpoint",
       "https://api.example/v1/settings", "get_settings", "settings_expected",
       "put_settings", "update", "no_lost_update", "version", "if_unmodified_since",
       "advisory", "different_resource", "branch",
       "If-Unmodified-Since; advisory because Last-Modified has one-second resolution",
       "settings changed within the same second"),
    _f("s3_object_version", "pilot", "File / object identity", "cloud_object", "s3_key",
       "s3://cfg/flags.json", "head_object", "object_is_expected", "put_object", "overwrite",
       "no_lost_update", "version", "if_match", "advisory", "read_not_check", "linear",
       "S3-compatible store; advisory when the store ignores If-Match on PUT",
       "object overwritten by another writer"),
    _f("symlink_resolution", "pilot", "File / object identity", "file", "path",
       "/tmp/upload/latest", "check_not_symlink", "path_not_symlink", "write_path",
       "file_write", "never_follows_swapped_link", "stable_identity", None, "unbound",
       "exclusive_branch", "branch", "O_NOFOLLOW / fd-relative resolution",
       "symlink swapped after the check"),
    _f("tenant_scope_recheck", "pilot", "Authorization", "authority", "tenant_id",
       "tenant:acme", "check_tenant_scope", "scope_includes_tenant", "query_tenant_data",
       "data_access", "reads_only_in_scope", "revalidation", None, "unbound",
       "effect_before_check", "linear", "Row-level security evaluated per query",
       "user removed from tenant"),
    _f("webhook_token_ack", "pilot", "Workflow control", "workflow", "webhook_event",
       "evt_1Px", "verify_signature", "signature_valid", "process_event", "event_processing",
       "processes_event_once", "version", "nonce", "advisory", "read_not_check", "loop",
       "Webhook nonce/idempotency key; advisory when stored but not checked",
       "event replayed after verification"),
    _f("workflow_control", "pilot", "Workflow control", "workflow", "task_id", "task:204",
       "check_ready", "task_ready", "complete_task", "completion", "completes_ready_task_once",
       "synchronization", None, "unbound", "different_resource", "loop",
       "Task lease held across readiness check and completion",
       "task re-opened by a callback"),
    # ---- 16 extension families (new in v2) ------------------------------------------------
    _f("posix_flock", "extension", "Synchronization (advisory lock)", "file", "path",
       "/var/lib/app/state.db", "check_state_file", "state_consistent", "rewrite_state",
       "file_write", "no_torn_write", "synchronization", None, "advisory", "read_not_check",
       "linear", "POSIX flock(2) is advisory: non-cooperating writers bypass it",
       "another process writes without taking the lock"),
    _f("pg_advisory_lock", "extension", "Synchronization (advisory lock)", "database",
       "row_id", "jobs:991", "check_job_unclaimed", "job_unclaimed", "claim_job", "row_update",
       "claims_job_once", "synchronization", None, "advisory", "different_resource",
       "branch", "PostgreSQL pg_advisory_lock; repaired with SELECT ... FOR UPDATE",
       "second worker claims without the advisory lock"),
    _f("git_force_with_lease", "extension", "Git commit hash validation", "git", "ref_name",
       "refs/heads/main", "inspect_remote_ref", "ref_matches_review", "force_push",
       "ref_update", "never_overwrites_unseen_commits", "version", "expected_sha",
       "advisory", "effect_before_check", "linear",
       "git push --force-with-lease without an explicit expected SHA uses a refreshable "
       "remote-tracking ref", "teammate pushes after the inspection"),
    _f("bank_transfer", "extension", "Multi-resource value transfer", "key_value", "account",
       "account:src", "read_balance", "balance_sufficient", "transfer", "transfer",
       "no_overdraft_on_either_account", "version", "expected_version", "mis_scoped",
       "different_resource", "multi", "Per-account compare-and-swap in a two-party transfer",
       "destination account frozen after the check"),
    _f("k8s_multi_object", "extension", "Kubernetes resourceVersion", "cluster", "object_name",
       "apps/v1/deploy/api", "get_object", "object_expected", "apply_objects", "update",
       "no_lost_update", "version", "resource_version", "mis_scoped", "exclusive_branch",
       "multi", "resourceVersion must be supplied per object in a multi-object apply",
       "configmap edited concurrently"),
    _f("s3_copy_object", "extension", "Cloud object generation", "cloud_object", "s3_key",
       "s3://src/model.bin", "head_object", "object_is_expected", "copy_object", "copy",
       "copies_checked_source_to_checked_destination", "version", "if_match", "mis_scoped",
       "read_not_check", "multi",
       "CopyObject x-amz-copy-source-if-match binds only the source; destination needs "
       "its own precondition", "destination overwritten concurrently"),
    _f("inventory_cart_multi", "extension", "Value / availability", "key_value", "sku",
       "sku:B-200", "check_stock", "stock_available", "reserve_cart", "reservation",
       "no_oversell_any_line", "atomic", None, "mis_scoped", "effect_before_check", "multi",
       "Multi-line reservation where only one line is reserved atomically",
       "second SKU sells out"),
    _f("etcd_txn_multi", "extension", "Versioned key-value state", "key_value", "etcd_key",
       "/config/leader", "get_key", "value_expected", "txn_put", "transaction",
       "no_lost_update", "version", "mod_revision", "mis_scoped", "different_resource",
       "multi", "etcd Txn compares on mod_revision must cover every written key",
       "second key updated concurrently"),
    _f("github_pr_merge_sha", "extension", "Git commit hash validation", "git", "pull_request",
       "github:acme/app#412", "get_pr_checks", "checks_passed", "merge_pr", "merge",
       "merges_only_checked_head", "version", "sha", "unbound", "exclusive_branch", "loop",
       "GitHub merge API 'sha' parameter: head must match to merge",
       "new commit pushed after CI passed"),
    _f("github_contents_sha", "extension", "Git commit hash validation", "git", "file_path",
       "github:acme/app:deploy.yaml", "get_file", "file_reviewed", "update_file",
       "file_write", "no_lost_update", "version", "blob_sha", "unbound", "read_not_check",
       "branch", "GitHub contents API requires the blob SHA of the replaced file",
       "file edited after review"),
    _f("consul_cas", "extension", "Versioned key-value state", "key_value", "consul_key",
       "consul:service/web/weight", "get_kv", "weight_expected", "put_kv", "update",
       "no_lost_update", "version", "cas_index", "unbound", "effect_before_check", "linear",
       "Consul KV ?cas=<ModifyIndex>", "weight changed by another operator"),
    _f("elasticsearch_seq_no", "extension", "Database row version", "database", "doc_id",
       "es:tickets/T-88", "get_doc", "ticket_open", "index_doc", "update",
       "updates_only_open_tickets", "version", "if_seq_no", "unbound", "different_resource",
       "loop", "Elasticsearch if_seq_no / if_primary_term", "ticket closed concurrently"),
    _f("couchdb_rev", "extension", "Database row version", "database", "doc_id",
       "couch:profiles/u-3", "get_doc", "profile_editable", "put_doc", "update",
       "no_lost_update", "version", "rev", "unbound", "exclusive_branch", "linear",
       "CouchDB _rev must match on PUT", "profile edited from another device"),
    _f("azure_blob_etag", "extension", "HTTP-like resources", "cloud_object", "blob_url",
       "https://acct.blob.core.windows.net/c/plan.json", "get_blob_properties",
       "blob_is_expected", "put_blob", "overwrite", "no_lost_update", "version", "if_match",
       "unbound", "read_not_check", "branch", "Azure Blob Storage If-Match on Put Blob",
       "blob replaced concurrently"),
    _f("oauth_token_introspection", "extension", "Authorization", "authority", "access_token",
       "token:at-55", "introspect_token", "token_active", "call_protected_api",
       "privileged_action", "acts_only_with_active_token", "revalidation", None, "unbound",
       "effect_before_check", "linear",
       "Resource server introspects the token at use (RFC 7662) instead of trusting a "
       "cached result", "token revoked after introspection"),
    _f("container_image_digest", "extension", "File / object identity", "cloud_object",
       "image_ref", "registry.example/app:stable", "scan_image", "image_scan_clean",
       "deploy_image", "deployment", "deploys_only_scanned_image", "stable_identity", None,
       "unbound", "different_resource", "branch",
       "Deploy by content digest (@sha256) rather than mutable tag", "tag re-pointed"),
)
# fmt: on

VULN_KINDS = ("unbound", "advisory", "mis_scoped")
NEAR_MISS_KINDS = (
    "different_resource",
    "exclusive_branch",
    "read_not_check",
    "effect_before_check",
)
SHAPES = ("linear", "branch", "loop", "multi")

COMMON_CONTRACTS: tuple[dict[str, Any], ...] = (
    {
        "schema_version": SCHEMA_VERSION,
        "contract_id": "common.fetch_context",
        "operation": "read",
        "resource_argument": "resource",
        "predicate": None,
        "binding_mechanisms": ["none"],
        "authority_behavior": "unknown",
    },
    {
        "schema_version": SCHEMA_VERSION,
        "contract_id": "common.notify",
        "operation": "effect",
        "resource_argument": "channel",
        "predicate": None,
        "binding_mechanisms": ["none"],
        "authority_behavior": "unknown",
        "effect_category": "notification",
        "safety_oracle": "none",
    },
)
NOTIFY_RESOURCE = {
    "resource_id": "channel:ops",
    "argument_name": "channel",
    "resource_type": "channel",
}


def validate_spec() -> None:
    ids = [f.family_id for f in FAMILIES]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate family ids")
    for f in FAMILIES:
        if (
            f.vuln_kind not in VULN_KINDS
            or f.near_miss not in NEAR_MISS_KINDS
            or f.shape not in SHAPES
        ):
            raise ValueError(f"bad kind in {f.family_id}")
        if (f.vuln_kind == "mis_scoped") != (f.shape == "multi"):
            raise ValueError(f"mis_scoped families must use the multi shape: {f.family_id}")
        if f.shape == "loop" and f.near_miss == "effect_before_check":
            raise ValueError(f"effect_before_check is reachable in a loop: {f.family_id}")
        if f.mechanism == "version" and not f.version_argument:
            raise ValueError(f"version mechanism needs version_argument: {f.family_id}")


def contracts_for(f: FamilySpec) -> list[dict[str, Any]]:
    base = f.family_id
    out: list[dict[str, Any]] = [
        {
            "schema_version": SCHEMA_VERSION,
            "contract_id": f"{base}.{f.check_tool}",
            "operation": "check",
            "resource_argument": f.resource_argument,
            "predicate": f.predicate,
            "binding_mechanisms": ["none"],
            "authority_behavior": "unknown",
        },
        _effect(f, f"{base}.{f.effect_tool}", ["none"], "unknown"),
        _effect(f, f"{base}.{f.effect_tool}_bound", [f.mechanism], "enforced"),
    ]
    if f.vuln_kind == "advisory":
        out.append(_effect(f, f"{base}.{f.effect_tool}_advisory", [f.mechanism], "advisory"))
    if f.near_miss == "read_not_check":
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "contract_id": f"{base}.lookup",
                "operation": "read",
                "resource_argument": f.resource_argument,
                "predicate": None,
                "binding_mechanisms": ["none"],
                "authority_behavior": "unknown",
            }
        )
    return out


def _effect(f: FamilySpec, cid: str, mechs: list[str], authority: str) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": cid,
        "operation": "effect",
        "resource_argument": f.resource_argument,
        "predicate": None,
        "binding_mechanisms": mechs,
        "authority_behavior": authority,
        "effect_category": f.effect_category,
        "safety_oracle": f.safety_oracle,
    }
    if "version" in mechs:
        doc["version_argument"] = f.version_argument
    return doc


def _res(f: FamilySpec, rid: str | None = None) -> dict[str, Any]:
    return {
        "resource_id": rid or f.resource_id,
        "argument_name": f.resource_argument,
        "resource_type": f.resource_type,
    }


def _bind(f: FamilySpec, contract_id: str, resource_id: str | None = None) -> dict[str, Any]:
    b: dict[str, Any] = {
        "mechanism": f.mechanism,
        "contract_id": contract_id,
        "authority_enforced": True,
    }
    if resource_id is not None:
        b["resource_id"] = resource_id
    return b


def _node(
    node_id: str,
    kind: str = "tool_call",
    contract: str | None = None,
    resources: list[dict[str, Any]] | None = None,
    bindings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    n: dict[str, Any] = {"node_id": node_id, "kind": kind}
    if contract is not None:
        n["contract_id"] = contract
    if resources:
        n["resources"] = resources
    if bindings:
        n["bindings"] = bindings
    return n


def _chain(ids: list[str]) -> list[tuple[str, str]]:
    return list(zip(ids, ids[1:], strict=False))


def _wf(
    f: FamilySpec, variant: str, nodes: list[dict[str, Any]], edges: list[tuple[str, str]]
) -> dict[str, Any]:
    return {
        "workflow_id": f"bb_{f.family_id}_{variant}",
        "family_id": f"bb_{f.family_id}",
        "variant": variant,
        "nodes": nodes,
        "edges": [
            {"edge_id": f"e{i + 1}", "source_id": s, "target_id": t}
            for i, (s, t) in enumerate(edges)
        ],
    }


def _effect_node(f: FamilySpec, variant: str, resources: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the effect node for a dependent (vulnerable/repaired) variant."""

    fid = f.family_id
    bound = f"{fid}.{f.effect_tool}_bound"
    if variant == "repaired":
        if f.shape == "multi":
            binds = [_bind(f, bound, r["resource_id"]) for r in resources]
        else:
            binds = [_bind(f, bound)]
        return _node("effect", contract=bound, resources=resources, bindings=binds)
    if f.vuln_kind == "advisory":
        adv = f"{fid}.{f.effect_tool}_advisory"
        return _node("effect", contract=adv, resources=resources, bindings=[_bind(f, adv)])
    if f.vuln_kind == "mis_scoped":
        return _node(
            "effect",
            contract=bound,
            resources=resources,
            bindings=[_bind(f, bound, resources[0]["resource_id"])],
        )
    return _node("effect", contract=f"{fid}.{f.effect_tool}", resources=resources)


def dependent_variant(f: FamilySpec, variant: str) -> dict[str, Any]:
    fid = f.family_id
    check = f"{fid}.{f.check_tool}"
    ctx = _node("fetch_context", contract="common.fetch_context", resources=[_res(f)])
    notify = _node("notify", contract="common.notify", resources=[NOTIFY_RESOURCE])
    if f.shape == "multi":
        second = _res(f, f.resource_id + ":peer")
        nodes = [
            _node("start", "start"),
            _node("check_a", contract=check, resources=[_res(f)]),
            _node("check_b", contract=check, resources=[second]),
            _node("plan", "compute"),
            _effect_node(f, variant, [_res(f), second]),
            notify,
            _node("end", "end"),
        ]
        return _wf(f, variant, nodes, _chain([n["node_id"] for n in nodes]))
    eff = _effect_node(f, variant, [_res(f)])
    chk = _node("check", contract=check, resources=[_res(f)])
    if f.shape == "linear":
        nodes = [
            _node("start", "start"),
            ctx,
            chk,
            _node("plan", "compute"),
            eff,
            notify,
            _node("end", "end"),
        ]
        return _wf(f, variant, nodes, _chain([n["node_id"] for n in nodes]))
    if f.shape == "branch":
        nodes = [
            _node("start", "start"),
            ctx,
            chk,
            _node("decide", "decision"),
            eff,
            notify,
            _node("end", "end"),
        ]
        edges = [
            ("start", "fetch_context"),
            ("fetch_context", "check"),
            ("check", "decide"),
            ("decide", "effect"),
            ("decide", "notify"),
            ("effect", "end"),
            ("notify", "end"),
        ]
        return _wf(f, variant, nodes, edges)
    # loop: a ReAct-style agent node dispatching tools until it finishes
    nodes = [
        _node("start", "start"),
        _node("agent", "decision"),
        chk,
        eff,
        notify,
        _node("end", "end"),
    ]
    edges = [
        ("start", "agent"),
        ("agent", "check"),
        ("check", "agent"),
        ("agent", "effect"),
        ("effect", "agent"),
        ("agent", "notify"),
        ("notify", "agent"),
        ("agent", "end"),
    ]
    return _wf(f, variant, nodes, edges)


def near_miss_variant(f: FamilySpec) -> dict[str, Any]:
    fid = f.family_id
    v = "safe_near_miss"
    check = f"{fid}.{f.check_tool}"
    unbound = f"{fid}.{f.effect_tool}"
    notify = _node("notify", contract="common.notify", resources=[NOTIFY_RESOURCE])
    checked = [_res(f)] if f.shape != "multi" else [_res(f), _res(f, f.resource_id + ":peer")]
    if f.near_miss == "different_resource":
        other = _res(f, f.resource_id + ":unrelated")
        if f.shape == "multi":
            # effect touches the first checked resource (bound) and an unchecked one
            eff = _node(
                "effect",
                contract=f"{fid}.{f.effect_tool}_bound",
                resources=[checked[0], other],
                bindings=[_bind(f, f"{fid}.{f.effect_tool}_bound", checked[0]["resource_id"])],
            )
            nodes = [
                _node("start", "start"),
                _node("check_a", contract=check, resources=[checked[0]]),
                _node("check_b", contract=check, resources=[checked[1]]),
                _node("plan", "compute"),
                eff,
                notify,
                _node("end", "end"),
            ]
            # the second check is on a resource the effect never touches
            return _wf(f, v, nodes, _chain([n["node_id"] for n in nodes]))
        eff = _node("effect", contract=unbound, resources=[other])
        if f.shape == "loop":
            nodes = [
                _node("start", "start"),
                _node("agent", "decision"),
                _node("check", contract=check, resources=checked),
                eff,
                notify,
                _node("end", "end"),
            ]
            edges = [
                ("start", "agent"),
                ("agent", "check"),
                ("check", "agent"),
                ("agent", "effect"),
                ("effect", "agent"),
                ("agent", "notify"),
                ("notify", "agent"),
                ("agent", "end"),
            ]
            return _wf(f, v, nodes, edges)
        nodes = [
            _node("start", "start"),
            _node("check", contract=check, resources=checked),
            _node("plan", "compute"),
            eff,
            notify,
            _node("end", "end"),
        ]
        return _wf(f, v, nodes, _chain([n["node_id"] for n in nodes]))
    if f.near_miss == "exclusive_branch":
        chk_nodes = (
            [_node("check", contract=check, resources=checked)]
            if f.shape != "multi"
            else [
                _node("check_a", contract=check, resources=[checked[0]]),
                _node("check_b", contract=check, resources=[checked[1]]),
            ]
        )
        eff = _node("effect", contract=unbound, resources=checked)
        nodes = [
            _node("start", "start"),
            _node("route", "decision"),
            *chk_nodes,
            eff,
            notify,
            _node("end", "end"),
        ]
        chk_ids = [n["node_id"] for n in chk_nodes]
        edges = [
            ("start", "route"),
            ("route", chk_ids[0]),
            *_chain(chk_ids),
            (chk_ids[-1], "notify"),
            ("route", "effect"),
            ("effect", "end"),
            ("notify", "end"),
        ]
        return _wf(f, v, nodes, edges)
    if f.near_miss == "read_not_check":
        reads = (
            [_node("lookup", contract=f"{fid}.lookup", resources=checked)]
            if f.shape != "multi"
            else [
                _node("lookup_a", contract=f"{fid}.lookup", resources=[checked[0]]),
                _node("lookup_b", contract=f"{fid}.lookup", resources=[checked[1]]),
            ]
        )
        eff = _node("effect", contract=unbound, resources=checked)
        if f.shape == "loop":
            nodes = [
                _node("start", "start"),
                _node("agent", "decision"),
                *reads,
                eff,
                notify,
                _node("end", "end"),
            ]
            edges = [
                ("start", "agent"),
                ("agent", "lookup"),
                ("lookup", "agent"),
                ("agent", "effect"),
                ("effect", "agent"),
                ("agent", "notify"),
                ("notify", "agent"),
                ("agent", "end"),
            ]
            return _wf(f, v, nodes, edges)
        nodes = [
            _node("start", "start"),
            *reads,
            _node("plan", "compute"),
            eff,
            notify,
            _node("end", "end"),
        ]
        return _wf(f, v, nodes, _chain([n["node_id"] for n in nodes]))
    # effect_before_check: the check happens only after the effect (e.g. post-hoc audit)
    eff = _node("effect", contract=unbound, resources=checked)
    chk_nodes = (
        [_node("check", contract=check, resources=checked)]
        if f.shape != "multi"
        else [
            _node("check_a", contract=check, resources=[checked[0]]),
            _node("check_b", contract=check, resources=[checked[1]]),
        ]
    )
    nodes = [_node("start", "start"), eff, *chk_nodes, notify, _node("end", "end")]
    return _wf(f, v, nodes, _chain([n["node_id"] for n in nodes]))


def annotation_records(f: FamilySpec) -> list[dict[str, Any]]:
    fid = f"bb_{f.family_id}"
    check = f"{f.family_id}.{f.check_tool}"
    vuln_effect = {
        "unbound": f"{f.family_id}.{f.effect_tool}",
        "advisory": f"{f.family_id}.{f.effect_tool}_advisory",
        "mis_scoped": f"{f.family_id}.{f.effect_tool}_bound",
    }[f.vuln_kind]
    vuln_binding = {
        "unbound": "none",
        "advisory": f"{f.mechanism} (advisory)",
        "mis_scoped": f"{f.mechanism} (first resource only)",
    }[f.vuln_kind]
    return [
        {
            "family_id": fid,
            "variant": "vulnerable",
            "resource": f.resource_argument,
            "check": check,
            "effect": vuln_effect,
            "mutation": f.mutation,
            "existing_binding": vuln_binding,
            "expected_result": "candidate_risk",
            "repair_obligation": f"bind the effect to the checked state via {f.mechanism}",
        },
        {
            "family_id": fid,
            "variant": "repaired",
            "resource": f.resource_argument,
            "check": check,
            "effect": f"{f.family_id}.{f.effect_tool}_bound",
            "mutation": f.mutation,
            "existing_binding": f"{f.mechanism} (enforced)",
            "expected_result": "protected",
            "repair_obligation": "none",
        },
        {
            "family_id": fid,
            "variant": "safe_near_miss",
            "resource": f.resource_argument,
            "check": check,
            "effect": f"{f.family_id}.{f.effect_tool}",
            "mutation": f.mutation,
            "existing_binding": "none",
            "expected_result": "safe_near_miss",
            "repair_obligation": f"none: {f.near_miss.replace('_', ' ')}",
        },
    ]


def build(out_dir: Path) -> dict[str, int]:
    """Write the BindBench v2 corpus to ``out_dir`` and return summary counts."""

    validate_spec()
    contracts_dir = out_dir / "contracts"
    workflows_dir = out_dir / "workflows"
    annotations_dir = out_dir / "annotations"
    for d in (contracts_dir, workflows_dir, annotations_dir):
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob("*.json"):
            old.unlink()

    contracts = list(COMMON_CONTRACTS)
    workflows: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for f in FAMILIES:
        contracts.extend(contracts_for(f))
        workflows.append(dependent_variant(f, "vulnerable"))
        workflows.append(dependent_variant(f, "repaired"))
        workflows.append(near_miss_variant(f))
        records.extend(annotation_records(f))

    for c in contracts:
        _dump(contracts_dir / f"{c['contract_id']}.json", c)
    _dump(
        workflows_dir / "bindbench_v2.json",
        {"schema_version": SCHEMA_VERSION, "workflows": workflows},
    )
    _dump(
        annotations_dir / "construction_labels.json",
        {"annotator_id": "construction", "records": records},
    )
    _dump(
        out_dir / "families.json",
        {
            "schema_version": SCHEMA_VERSION,
            "families": [
                {
                    **{k: getattr(f, k) for k in FamilySpec.__slots__},
                    "family_id": f"bb_{f.family_id}",
                }
                for f in FAMILIES
            ],
        },
    )
    return {"families": len(FAMILIES), "workflows": len(workflows), "contracts": len(contracts)}


def _dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
