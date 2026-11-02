"""Catalog of real tool APIs with hand-written AgentLint contracts.

Each entry records the tool's public name, its input parameters (names as documented by the
provider), a one-line description, the documentation it was derived from, and the contract
we wrote for it. ``judgement`` records the documentation fact a contract author had to look
up to fill ``authority_behavior`` (the field that cannot be read off a parameter list).

The catalog serves two purposes: it measures contract-authoring effort on real tools, and it
supplies the tool library from which the benign-workflow corpus is assembled.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DOCS = {
    "github": "https://docs.github.com/en/rest (pulls, repos/contents, checks)",
    "fs": "https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem",
    "k8s": "https://kubernetes.io/docs/reference/using-api/api-concepts/#resource-versions",
    "s3": "https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-requests.html",
    "ddb": "https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html",
    "gcs": "https://cloud.google.com/storage/docs/request-preconditions",
    "stripe": "https://docs.stripe.com/api/payment_intents/capture",
    "redis": "https://redis.io/docs/latest/develop/interact/transactions/",
    "etcd": "https://etcd.io/docs/v3.5/learning/api/#transaction",
    "consul": "https://developer.hashicorp.com/consul/api-docs/kv",
    "es": "https://www.elastic.co/guide/en/elasticsearch/reference/current/optimistic-concurrency-control.html",
    "azure": "https://learn.microsoft.com/en-us/rest/api/storageservices/specifying-conditional-headers-for-blob-service-operations",
    "slack": "https://api.slack.com/methods/chat.postMessage",
    "git": "https://git-scm.com/docs/git-push#Documentation/git-push.txt---force-with-leaseltrefnamegt",
    "pg": "https://github.com/modelcontextprotocol/servers-archived/tree/main/src/postgres",
    "posix": "https://man7.org/linux/man-pages/man2/flock.2.html",
}


def _t(
    service: str,
    name: str,
    params: list[str],
    required: list[str],
    description: str,
    operation: str,
    resource_argument: str,
    predicate: str | None = None,
    mechanisms: tuple[str, ...] = ("none",),
    authority: str = "unknown",
    version_argument: str | None = None,
    effect_category: str | None = None,
    judgement: str | None = None,
) -> dict[str, Any]:
    contract: dict[str, Any] = {
        "schema_version": 1,
        "contract_id": f"{service}.{name}",
        "operation": operation,
        "resource_argument": resource_argument,
        "predicate": predicate,
        "binding_mechanisms": list(mechanisms),
        "authority_behavior": authority,
    }
    if version_argument is not None:
        contract["version_argument"] = version_argument
    if effect_category is not None:
        contract["effect_category"] = effect_category
        contract["safety_oracle"] = f"{effect_category}_on_checked_state"
    return {
        "service": service,
        "name": name,
        "description": description,
        "parameters": params,
        "required": required,
        "doc": DOCS[service],
        "judgement": judgement,
        "contract": contract,
    }


# fmt: off
CATALOG: tuple[dict[str, Any], ...] = (
    # GitHub REST / github-mcp-server
    _t("github", "get_pull_request", ["owner", "repo", "pull_number"], ["owner", "repo", "pull_number"],
       "Get details of a pull request", "read", "pull_number"),
    _t("github", "get_pull_request_status", ["owner", "repo", "pull_number"], ["owner", "repo", "pull_number"],
       "Get combined status checks for a pull request head", "check", "pull_number", "checks_passed"),
    _t("github", "merge_pull_request", ["owner", "repo", "pull_number", "sha", "merge_method", "commit_title"],
       ["owner", "repo", "pull_number"], "Merge a pull request", "effect", "pull_number",
       mechanisms=("version",), authority="enforced", version_argument="sha", effect_category="merge",
       judgement="409 when 'sha' does not match the head; binding only if the caller passes sha"),
    _t("github", "get_file_contents", ["owner", "repo", "path", "ref"], ["owner", "repo", "path"],
       "Get file or directory contents", "read", "path"),
    _t("github", "create_or_update_file", ["owner", "repo", "path", "content", "message", "branch", "sha"],
       ["owner", "repo", "path", "content", "message"], "Create or update a file", "effect", "path",
       mechanisms=("version",), authority="enforced", version_argument="sha", effect_category="file_write",
       judgement="409 when the blob sha of the replaced file is stale"),
    _t("github", "delete_file", ["owner", "repo", "path", "message", "sha", "branch"],
       ["owner", "repo", "path", "message", "sha"], "Delete a file", "effect", "path",
       mechanisms=("version",), authority="enforced", version_argument="sha", effect_category="deletion",
       judgement="409 on stale blob sha"),
    # MCP filesystem server
    _t("fs", "read_file", ["path"], ["path"], "Read the complete contents of a file", "read", "path"),
    _t("fs", "get_file_info", ["path"], ["path"], "Retrieve metadata (size, times, permissions) of a file",
       "check", "path", "file_attributes_acceptable"),
    _t("fs", "list_directory", ["path"], ["path"], "List directory entries", "read", "path"),
    _t("fs", "write_file", ["path", "content"], ["path", "content"], "Create or overwrite a file",
       "effect", "path", effect_category="file_write",
       judgement="no precondition parameter; path re-resolved at write"),
    _t("fs", "edit_file", ["path", "edits", "dryRun"], ["path", "edits"],
       "Apply line-based edits to a text file", "effect", "path", effect_category="file_write",
       judgement="edits are matched against current text, not a checked version"),
    _t("fs", "move_file", ["source", "destination"], ["source", "destination"], "Move or rename a file",
       "effect", "source", effect_category="rename"),
    # Kubernetes API
    _t("k8s", "get_deployment", ["name", "namespace"], ["name", "namespace"], "Read a Deployment",
       "check", "name", "spec_expected"),
    _t("k8s", "replace_deployment", ["name", "namespace", "body", "resourceVersion"], ["name", "namespace", "body"],
       "Replace a Deployment (PUT)", "effect", "name", mechanisms=("version",), authority="enforced",
       version_argument="resourceVersion", effect_category="update",
       judgement="409 Conflict when metadata.resourceVersion is stale"),
    _t("k8s", "patch_deployment", ["name", "namespace", "body"], ["name", "namespace", "body"],
       "Merge-patch a Deployment", "effect", "name", effect_category="update",
       judgement="merge patch without resourceVersion is applied unconditionally"),
    _t("k8s", "delete_deployment", ["name", "namespace", "preconditions"], ["name", "namespace"],
       "Delete a Deployment", "effect", "name", mechanisms=("version",), authority="enforced",
       version_argument="preconditions", effect_category="deletion",
       judgement="preconditions.resourceVersion / uid enforced by the API server"),
    # AWS S3
    _t("s3", "head_object", ["Bucket", "Key", "IfMatch"], ["Bucket", "Key"], "Retrieve object metadata",
       "check", "Key", "object_is_expected"),
    _t("s3", "get_object", ["Bucket", "Key", "VersionId"], ["Bucket", "Key"], "Retrieve an object",
       "read", "Key"),
    _t("s3", "put_object", ["Bucket", "Key", "Body", "IfMatch", "IfNoneMatch"], ["Bucket", "Key", "Body"],
       "Store an object", "effect", "Key", mechanisms=("version",), authority="enforced",
       version_argument="IfMatch", effect_category="overwrite",
       judgement="412 on ETag mismatch (S3 conditional writes); not enforced by all S3-compatible stores"),
    _t("s3", "delete_object", ["Bucket", "Key", "VersionId"], ["Bucket", "Key"], "Delete an object",
       "effect", "Key", mechanisms=("stable_identity",), authority="enforced", effect_category="deletion",
       judgement="VersionId deletes exactly the checked version"),
    _t("s3", "copy_object", ["Bucket", "Key", "CopySource", "CopySourceIfMatch"], ["Bucket", "Key", "CopySource"],
       "Copy an object", "effect", "CopySource", mechanisms=("version",), authority="enforced",
       version_argument="CopySourceIfMatch", effect_category="copy",
       judgement="precondition covers the source only"),
    # DynamoDB
    _t("ddb", "get_item", ["TableName", "Key", "ConsistentRead"], ["TableName", "Key"], "Read an item",
       "check", "Key", "item_state_acceptable"),
    _t("ddb", "update_item", ["TableName", "Key", "UpdateExpression", "ConditionExpression"],
       ["TableName", "Key"], "Update an item", "effect", "Key", mechanisms=("atomic",), authority="enforced",
       effect_category="update",
       judgement="ConditionalCheckFailedException when ConditionExpression fails"),
    # Google Cloud Storage
    _t("gcs", "objects_get", ["bucket", "object"], ["bucket", "object"], "Get object metadata",
       "check", "object", "object_is_expected"),
    _t("gcs", "objects_insert", ["bucket", "name", "ifGenerationMatch"], ["bucket", "name"], "Upload an object",
       "effect", "name", mechanisms=("version",), authority="enforced", version_argument="ifGenerationMatch",
       effect_category="overwrite", judgement="412 Precondition Failed on generation mismatch"),
    _t("gcs", "objects_delete", ["bucket", "object", "ifGenerationMatch"], ["bucket", "object"],
       "Delete an object", "effect", "object", mechanisms=("version",), authority="enforced",
       version_argument="ifGenerationMatch", effect_category="deletion",
       judgement="412 on generation mismatch"),
    # Stripe
    _t("stripe", "retrieve_payment_intent", ["id"], ["id"], "Retrieve a PaymentIntent", "check", "id",
       "requires_capture"),
    _t("stripe", "capture_payment_intent", ["id", "amount_to_capture"], ["id"], "Capture a PaymentIntent",
       "effect", "id", mechanisms=("revalidation",), authority="enforced", effect_category="capture",
       judgement="server rejects capture unless status is requires_capture"),
    _t("stripe", "create_refund", ["payment_intent", "amount"], ["payment_intent"], "Refund a charge",
       "effect", "payment_intent", mechanisms=("revalidation",), authority="enforced",
       effect_category="refund", judgement="server rejects amounts above the refundable balance"),
    # Redis
    _t("redis", "get", ["key"], ["key"], "Get the value of a key", "check", "key", "value_acceptable"),
    _t("redis", "set", ["key", "value"], ["key", "value"], "Set the value of a key", "effect", "key",
       effect_category="overwrite", judgement="unconditional"),
    _t("redis", "exec_watched", ["key", "commands"], ["key", "commands"], "WATCH key; MULTI; ...; EXEC",
       "effect", "key", mechanisms=("atomic",), authority="enforced", effect_category="transaction",
       judgement="EXEC aborts if a watched key changed"),
    # etcd v3
    _t("etcd", "range", ["key"], ["key"], "Read a key", "check", "key", "value_expected"),
    _t("etcd", "txn", ["key", "compare", "success", "failure"], ["compare", "success"],
       "Transaction guarded by compare predicates", "effect", "key", mechanisms=("version",),
       authority="enforced", version_argument="compare", effect_category="transaction",
       judgement="compare on mod_revision evaluated atomically; covers only compared keys"),
    _t("etcd", "put", ["key", "value"], ["key", "value"], "Write a key", "effect", "key",
       effect_category="overwrite"),
    # Consul KV
    _t("consul", "kv_get", ["key"], ["key"], "Read a key", "check", "key", "value_expected"),
    _t("consul", "kv_put", ["key", "value", "cas"], ["key", "value"], "Write a key", "effect", "key",
       mechanisms=("version",), authority="enforced", version_argument="cas", effect_category="overwrite",
       judgement="?cas=<ModifyIndex> returns false on mismatch"),
    # Elasticsearch
    _t("es", "get_doc", ["index", "id"], ["index", "id"], "Get a document", "check", "id", "doc_state_acceptable"),
    _t("es", "index_doc", ["index", "id", "document", "if_seq_no", "if_primary_term"], ["index", "document"],
       "Index a document", "effect", "id", mechanisms=("version",), authority="enforced",
       version_argument="if_seq_no", effect_category="update",
       judgement="409 version_conflict_engine_exception"),
    # Azure Blob
    _t("azure", "get_blob_properties", ["container", "blob"], ["container", "blob"], "Get blob properties",
       "check", "blob", "blob_is_expected"),
    _t("azure", "put_blob", ["container", "blob", "body", "if_match"], ["container", "blob", "body"],
       "Upload a blob", "effect", "blob", mechanisms=("version",), authority="enforced",
       version_argument="if_match", effect_category="overwrite", judgement="412 on ETag mismatch"),
    # Slack
    _t("slack", "chat_post_message", ["channel", "text", "thread_ts"], ["channel", "text"], "Post a message",
       "effect", "channel", effect_category="notification"),
    # git CLI
    _t("git", "ls_remote", ["remote", "ref"], ["remote", "ref"], "Read a remote ref", "check", "ref",
       "ref_matches_review"),
    _t("git", "push_force_with_lease", ["remote", "ref", "expect"], ["remote", "ref"],
       "git push --force-with-lease[=ref:expect]", "effect", "ref", mechanisms=("version",),
       authority="enforced", version_argument="expect", effect_category="ref_update",
       judgement="enforced only with an explicit expect; the implicit lease is the local "
                 "remote-tracking ref, which a background fetch refreshes, so it is no binding"),
    # POSIX advisory locking
    _t("posix", "flock_write", ["path", "content", "lock"], ["path", "content"],
       "Write a file while holding flock(LOCK_EX) on it", "effect", "path",
       mechanisms=("synchronization",), authority="advisory", effect_category="file_write",
       judgement="flock(2) locks are advisory: writers that do not call flock are not blocked"),
    # Postgres MCP server (read-only query tool)
    _t("pg", "query", ["sql"], ["sql"], "Run a read-only SQL query", "read", "sql",
       judgement="resource is embedded in SQL text; contract cannot name a row"),
)
# fmt: on


def write_catalog(out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "catalog.json").write_text(
        json.dumps({"schema_version": 1, "tools": list(CATALOG)}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    contracts = out_dir / "contracts"
    contracts.mkdir(exist_ok=True)
    for old in contracts.glob("*.json"):
        old.unlink()
    for tool in CATALOG:
        c = tool["contract"]
        (contracts / f"{c['contract_id']}.json").write_text(
            json.dumps(c, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return len(CATALOG)
