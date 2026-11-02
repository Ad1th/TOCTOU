"""Executable LangChain tools over simulated, versioned service backends.

Each tool mirrors the parameter names of the real API it stands for (see
``agentlint.benchmark.tool_catalog``). The backend tracks a version per resource, so a
concurrent mutation is observable, and it records a *violation* whenever an effect is
applied to a resource whose version changed after the most recent check of it -- the
runtime safety oracle used for dynamic confirmation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from langchain_core.tools import ToolException, tool


@dataclass
class Backend:
    versions: dict[str, int] = field(default_factory=dict)
    checked: dict[str, int] = field(default_factory=dict)
    violations: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    applied: list[str] = field(default_factory=list)
    adversary: Callable[[str], None] | None = None

    def version(self, key: str) -> int:
        return self.versions.setdefault(key, 1)

    def token(self, key: str) -> str:
        return f"v{self.version(key)}"

    def mutate(self, key: str) -> None:
        self.versions[key] = self.version(key) + 1

    def check(self, key: str) -> str:
        self.checked[key] = self.version(key)
        observed = self.token(key)  # the caller sees the state as of the check
        if self.adversary is not None:
            self.adversary(key)  # worst-case interleaving: mutate right after the check
        return observed

    def effect(
        self, key: str, *, expected: str | None = None, guard: bool = False, advisory: bool = False
    ) -> str:
        """Apply an effect. ``expected`` is a version token; ``guard`` means the authority
        re-validates intrinsically (atomic/revalidation); ``advisory`` ignores ``expected``."""

        stale = key in self.checked and self.version(key) != self.checked[key]
        if expected is not None and not advisory and expected != self.token(key):
            self.rejected.append(key)
            raise ToolException(f"409 Conflict: {key} changed (expected {expected})")
        if guard and stale:
            self.rejected.append(key)
            raise ToolException(f"412 Precondition Failed: {key} re-validation failed")
        if stale:
            self.violations.append(key)
        self.applied.append(key)
        self.mutate(key)
        return "ok"

    def reset(self) -> None:
        self.versions.clear()
        self.checked.clear()
        self.violations.clear()
        self.rejected.clear()
        self.applied.clear()
        self.adversary = None


BACKEND = Backend()


# ---- GitHub
@tool
def get_pull_request_status(owner: str, repo: str, pull_number: int) -> dict[str, Any]:
    """Get combined CI status and head SHA of a pull request."""
    sha = BACKEND.check(f"pr:{pull_number}")
    return {"state": "success", "head_sha": sha}


@tool
def merge_pull_request(owner: str, repo: str, pull_number: int, sha: str | None = None) -> str:
    """Merge a pull request; if sha is given the head must match."""
    return BACKEND.effect(f"pr:{pull_number}", expected=sha)


@tool
def get_file_contents(owner: str, repo: str, path: str) -> str:
    """Read a repository file."""
    return f"contents of {path}"


# ---- Kubernetes
@tool
def get_deployment(name: str, namespace: str) -> dict[str, Any]:
    """Read a Deployment."""
    rv = BACKEND.check(f"deploy:{namespace}/{name}")
    return {"replicas": 3, "resourceVersion": rv}


@tool
def replace_deployment(
    name: str, namespace: str, body: dict[str, Any], resourceVersion: str | None = None
) -> str:  # noqa: N803 (API name)
    """Replace a Deployment; resourceVersion enables optimistic concurrency."""
    return BACKEND.effect(f"deploy:{namespace}/{name}", expected=resourceVersion)


# ---- S3
@tool
def head_object(Bucket: str, Key: str) -> dict[str, Any]:  # noqa: N803
    """Retrieve object metadata."""
    return {"ETag": BACKEND.check(f"s3:{Bucket}/{Key}")}


@tool
def put_object(Bucket: str, Key: str, Body: str, IfMatch: str | None = None) -> str:  # noqa: N803
    """Store an object; IfMatch makes the write conditional on the ETag."""
    return BACKEND.effect(f"s3:{Bucket}/{Key}", expected=IfMatch)


# ---- Stripe
@tool
def retrieve_payment_intent(id: str) -> dict[str, Any]:  # noqa: A002
    """Retrieve a PaymentIntent."""
    BACKEND.check(f"pi:{id}")
    return {"status": "requires_capture"}


@tool
def capture_payment_intent(id: str) -> str:  # noqa: A002
    """Capture a PaymentIntent; the processor re-validates its status."""
    return BACKEND.effect(f"pi:{id}", guard=True)


# ---- filesystem
@tool
def get_file_info(path: str) -> dict[str, Any]:
    """Get file metadata."""
    BACKEND.check(f"file:{path}")
    return {"mode": "0644", "owner": "app"}


@tool
def write_file(path: str, content: str) -> str:
    """Create or overwrite a file by path."""
    return BACKEND.effect(f"file:{path}")


@tool
def read_file(path: str) -> str:
    """Read a file."""
    return f"contents of {path}"


# ---- Redis
@tool
def redis_get(key: str) -> str:
    """GET key."""
    return BACKEND.check(f"redis:{key}")


@tool
def redis_set(key: str, value: str) -> str:
    """SET key value (unconditional)."""
    return BACKEND.effect(f"redis:{key}")


@tool
def exec_watched(key: str, commands: list[str]) -> str:
    """WATCH key; MULTI; commands; EXEC (aborts if key changed)."""
    return BACKEND.effect(f"redis:{key}", guard=True)


# ---- Consul
@tool
def kv_get(key: str) -> dict[str, Any]:
    """Read a Consul key."""
    return {"ModifyIndex": BACKEND.check(f"consul:{key}")}


@tool
def kv_put(key: str, value: str, cas: str | None = None) -> str:
    """Write a Consul key; cas=<ModifyIndex> makes it conditional."""
    return BACKEND.effect(f"consul:{key}", expected=cas)


# ---- git
@tool
def ls_remote(remote: str, ref: str) -> str:
    """Read a remote ref."""
    return BACKEND.check(f"git:{ref}")


@tool
def push_force_with_lease(remote: str, ref: str, expect: str | None = None) -> str:
    """git push --force-with-lease[=ref:expect]."""
    if expect is None:
        # implicit lease = local remote-tracking ref, refreshed by background fetch
        return BACKEND.effect(f"git:{ref}", expected=BACKEND.token(f"git:{ref}"), advisory=True)
    return BACKEND.effect(f"git:{ref}", expected=expect)


# ---- Slack
@tool
def chat_post_message(channel: str, text: str) -> str:
    """Post a message."""
    return "ts=1"


ALL_TOOLS = (
    get_pull_request_status,
    merge_pull_request,
    get_file_contents,
    get_deployment,
    replace_deployment,
    head_object,
    put_object,
    retrieve_payment_intent,
    capture_payment_intent,
    get_file_info,
    write_file,
    read_file,
    redis_get,
    redis_set,
    exec_watched,
    kv_get,
    kv_put,
    ls_remote,
    push_force_with_lease,
    chat_post_message,
)

# tool name -> catalog contract id
CONTRACT_OF = {
    "get_pull_request_status": "github.get_pull_request_status",
    "merge_pull_request": "github.merge_pull_request",
    "get_file_contents": "github.get_file_contents",
    "get_deployment": "k8s.get_deployment",
    "replace_deployment": "k8s.replace_deployment",
    "head_object": "s3.head_object",
    "put_object": "s3.put_object",
    "retrieve_payment_intent": "stripe.retrieve_payment_intent",
    "capture_payment_intent": "stripe.capture_payment_intent",
    "get_file_info": "fs.get_file_info",
    "write_file": "fs.write_file",
    "read_file": "fs.read_file",
    "redis_get": "redis.get",
    "redis_set": "redis.set",
    "exec_watched": "redis.exec_watched",
    "kv_get": "consul.kv_get",
    "kv_put": "consul.kv_put",
    "ls_remote": "git.ls_remote",
    "push_force_with_lease": "git.push_force_with_lease",
    "chat_post_message": "slack.chat_post_message",
}


def registry() -> dict[str, Any]:
    """Map LangChain tool names to AgentLint contracts from the real-tool catalog."""

    from agentlint.benchmark.tool_catalog import CATALOG
    from agentlint.contracts.validation import validate_contract

    by_id = {t["contract"]["contract_id"]: validate_contract(t["contract"]) for t in CATALOG}
    return {name: by_id[cid] for name, cid in CONTRACT_OF.items()}
