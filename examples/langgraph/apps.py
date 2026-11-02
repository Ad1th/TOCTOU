"""LangGraph applications used to evaluate the AgentLint frontends.

``GRAPH_APPS`` are explicit ``StateGraph`` pipelines; their node functions call LangChain
tools and are analyzed statically from source. ``AGENT_APPS`` are ReAct agents built with
``langgraph.prebuilt.create_react_agent``; a deterministic scripted chat model plays the LLM
so runs are reproducible, and the executed message history is analyzed by the trace frontend.
Each app has an expected label: ``candidate_risk`` or ``protected``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.graph import END, START, StateGraph

from examples.langgraph.tools import (
    capture_payment_intent,
    chat_post_message,
    exec_watched,
    get_deployment,
    get_file_contents,
    get_file_info,
    get_pull_request_status,
    head_object,
    ls_remote,
    merge_pull_request,
    push_force_with_lease,
    put_object,
    read_file,
    redis_get,
    redis_set,
    replace_deployment,
    retrieve_payment_intent,
    write_file,
)


class St(TypedDict, total=False):
    pr: int
    head: str
    ok: bool
    name: str
    rv: str
    key: str
    etag: str
    pi: str
    path: str
    ref: str
    sha: str


# --------------------------------------------------------------------------- graphs
# PR merge bot: check CI, then merge (vulnerable: no sha; repaired: sha from the check)


def ci_check(state: St) -> St:
    status = get_pull_request_status.invoke(
        {"owner": "acme", "repo": "app", "pull_number": state["pr"]}
    )
    return {"ok": status["state"] == "success", "head": status["head_sha"]}


def merge_unbound(state: St) -> St:
    merge_pull_request.invoke({"owner": "acme", "repo": "app", "pull_number": state["pr"]})
    return {}


def merge_bound(state: St) -> St:
    merge_pull_request.invoke(
        {"owner": "acme", "repo": "app", "pull_number": state["pr"], "sha": state["head"]}
    )
    return {}


def announce(state: St) -> St:
    chat_post_message.invoke({"channel": "#release", "text": f"merged #{state['pr']}"})
    return {}


def _route_ci(state: St) -> str:
    return "merge" if state.get("ok") else END


def pr_merge_graph(merge: Callable[[St], St]) -> StateGraph:
    g = StateGraph(St)
    g.add_node("ci_check", ci_check)
    g.add_node("merge", merge)
    g.add_node("announce", announce)
    g.add_edge(START, "ci_check")
    g.add_conditional_edges("ci_check", _route_ci, {"merge": "merge", END: END})
    g.add_edge("merge", "announce")
    g.add_edge("announce", END)
    return g


# Deployment scaler: read, then replace (vulnerable: no resourceVersion)


def read_deploy(state: St) -> St:
    d = get_deployment.invoke({"name": state["name"], "namespace": "prod"})
    return {"rv": d["resourceVersion"], "ok": d["replicas"] < 10}


def scale_unbound(state: St) -> St:
    replace_deployment.invoke({"name": state["name"], "namespace": "prod", "body": {"replicas": 6}})
    return {}


def scale_bound(state: St) -> St:
    replace_deployment.invoke(
        {
            "name": state["name"],
            "namespace": "prod",
            "body": {"replicas": 6},
            "resourceVersion": state["rv"],
        }
    )
    return {}


def scaler_graph(scale: Callable[[St], St]) -> StateGraph:
    g = StateGraph(St)
    g.add_node("read_deploy", read_deploy)
    g.add_node("scale", scale)
    g.add_edge(START, "read_deploy")
    g.add_edge("read_deploy", "scale")
    g.add_edge("scale", END)
    return g


# Config updater: head, then put (vulnerable: no IfMatch)


def head_cfg(state: St) -> St:
    return {"etag": head_object.invoke({"Bucket": "cfg", "Key": state["key"]})["ETag"]}


def put_unbound(state: St) -> St:
    put_object.invoke({"Bucket": "cfg", "Key": state["key"], "Body": "{}"})
    return {}


def put_bound(state: St) -> St:
    put_object.invoke(
        {"Bucket": "cfg", "Key": state["key"], "Body": "{}", "IfMatch": state["etag"]}
    )
    return {}


def config_graph(put: Callable[[St], St]) -> StateGraph:
    g = StateGraph(St)
    g.add_node("head_cfg", head_cfg)
    g.add_node("put", put)
    g.add_edge(START, "head_cfg")
    g.add_edge("head_cfg", "put")
    g.add_edge("put", END)
    return g


# Payment capture: the processor re-validates at capture (protected without a token)


def check_pi(state: St) -> St:
    return {
        "ok": retrieve_payment_intent.invoke({"id": state["pi"]})["status"] == "requires_capture"
    }


def capture(state: St) -> St:
    capture_payment_intent.invoke({"id": state["pi"]})
    return {}


def payment_graph() -> StateGraph:
    g = StateGraph(St)
    g.add_node("check_pi", check_pi)
    g.add_node("capture", capture)
    g.add_edge(START, "check_pi")
    g.add_conditional_edges(
        "check_pi", lambda s: "capture" if s.get("ok") else END, {"capture": "capture", END: END}
    )
    g.add_edge("capture", END)
    return g


# File cleanup: stat then write by path (no binding available in this tool set)


def stat_and_write(state: St) -> St:
    info = get_file_info.invoke({"path": state["path"]})
    if info["owner"] == "app":
        write_file.invoke({"path": state["path"], "content": ""})
    return {}


def file_graph() -> StateGraph:
    g = StateGraph(St)
    g.add_node("stat_and_write", stat_and_write)
    g.add_edge(START, "stat_and_write")
    g.add_edge("stat_and_write", END)
    return g


# Ledger: redis read then set (vulnerable) or WATCH/MULTI/EXEC (repaired)


def read_balance(state: St) -> St:
    redis_get.invoke({"key": state["key"]})
    return {}


def debit_set(state: St) -> St:
    redis_set.invoke({"key": state["key"], "value": "90"})
    return {}


def debit_watched(state: St) -> St:
    exec_watched.invoke({"key": state["key"], "commands": ["DECRBY 10"]})
    return {}


def ledger_graph(debit: Callable[[St], St]) -> StateGraph:
    g = StateGraph(St)
    g.add_node("read_balance", read_balance)
    g.add_node("debit", debit)
    g.add_edge(START, "read_balance")
    g.add_edge("read_balance", "debit")
    g.add_edge("debit", END)
    return g


# Release: inspect remote ref then force-push (implicit lease vs explicit expect)


def inspect_ref(state: St) -> St:
    return {"sha": ls_remote.invoke({"remote": "origin", "ref": state["ref"]})}


def push_implicit(state: St) -> St:
    push_force_with_lease.invoke({"remote": "origin", "ref": state["ref"]})
    return {}


def push_explicit(state: St) -> St:
    push_force_with_lease.invoke({"remote": "origin", "ref": state["ref"], "expect": state["sha"]})
    return {}


def release_graph(push: Callable[[St], St]) -> StateGraph:
    g = StateGraph(St)
    g.add_node("inspect_ref", inspect_ref)
    g.add_node("push", push)
    g.add_edge(START, "inspect_ref")
    g.add_edge("inspect_ref", "push")
    g.add_edge("push", END)
    return g


# Benign: read-only research, and a status report that only posts to chat


def research(state: St) -> St:
    get_file_contents.invoke({"owner": "acme", "repo": "app", "path": "README.md"})
    read_file.invoke({"path": "/docs/notes.md"})
    return {}


def research_graph() -> StateGraph:
    g = StateGraph(St)
    g.add_node("research", research)
    g.add_edge(START, "research")
    g.add_edge("research", END)
    return g


def report_graph() -> StateGraph:
    g = StateGraph(St)
    g.add_node("ci_check", ci_check)
    g.add_node("announce", announce)
    g.add_edge(START, "ci_check")
    g.add_edge("ci_check", "announce")
    g.add_edge("announce", END)
    return g


@dataclass(frozen=True)
class GraphApp:
    name: str
    build: Callable[[], StateGraph]
    state: dict[str, Any]
    expected: str


GRAPH_APPS: tuple[GraphApp, ...] = (
    GraphApp(
        "pr_merge_unbound", lambda: pr_merge_graph(merge_unbound), {"pr": 412}, "candidate_risk"
    ),
    GraphApp("pr_merge_bound", lambda: pr_merge_graph(merge_bound), {"pr": 412}, "protected"),
    GraphApp(
        "k8s_scale_unbound", lambda: scaler_graph(scale_unbound), {"name": "web"}, "candidate_risk"
    ),
    GraphApp("k8s_scale_bound", lambda: scaler_graph(scale_bound), {"name": "web"}, "protected"),
    GraphApp(
        "s3_config_unbound",
        lambda: config_graph(put_unbound),
        {"key": "flags.json"},
        "candidate_risk",
    ),
    GraphApp(
        "s3_config_bound", lambda: config_graph(put_bound), {"key": "flags.json"}, "protected"
    ),
    GraphApp("payment_capture", payment_graph, {"pi": "pi_3Nx"}, "protected"),
    GraphApp("file_cleanup", file_graph, {"path": "/srv/tmp/report"}, "candidate_risk"),
    GraphApp("ledger_set", lambda: ledger_graph(debit_set), {"key": "acct:1"}, "candidate_risk"),
    GraphApp("ledger_watched", lambda: ledger_graph(debit_watched), {"key": "acct:1"}, "protected"),
    GraphApp(
        "release_implicit_lease",
        lambda: release_graph(push_implicit),
        {"ref": "main"},
        "candidate_risk",
    ),
    GraphApp(
        "release_explicit_lease", lambda: release_graph(push_explicit), {"ref": "main"}, "protected"
    ),
    GraphApp("research_readonly", research_graph, {}, "protected"),
    GraphApp("ci_report", report_graph, {"pr": 412}, "protected"),
)


# --------------------------------------------------------------------------- ReAct agents


class ScriptedChatModel(BaseChatModel):
    """A deterministic stand-in for an LLM: a policy maps the history to the next message."""

    policy: Callable[[list[BaseMessage]], AIMessage]

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Any, **kwargs: Any) -> ScriptedChatModel:
        return self

    def _generate(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self.policy(messages))])


Step = tuple[str, Callable[[dict[str, Any]], dict[str, Any]]]


def plan_policy(steps: list[Step]) -> Callable[[list[BaseMessage]], AIMessage]:
    """Emit one tool call per turn; arguments may use earlier tool outputs."""

    def policy(messages: list[BaseMessage]) -> AIMessage:
        outputs: dict[str, Any] = {}
        for m in messages:
            if isinstance(m, ToolMessage):
                outputs[m.name] = m.content
        done = sum(isinstance(m, ToolMessage) for m in messages)
        if done >= len(steps) or any(
            isinstance(m, ToolMessage) and m.status == "error" for m in messages
        ):
            return AIMessage(content="done")
        name, args = steps[done]
        return AIMessage(
            content="", tool_calls=[{"name": name, "args": args(outputs), "id": f"call_{done}"}]
        )

    return policy


def _field(outputs: dict[str, Any], tool: str, key: str) -> str:
    import ast as _ast

    raw = outputs[tool]
    value = _ast.literal_eval(raw) if isinstance(raw, str) and raw.startswith("{") else raw
    return value[key] if isinstance(value, dict) else value


@dataclass(frozen=True)
class AgentApp:
    name: str
    steps: tuple[Step, ...]
    expected: str


AGENT_APPS: tuple[AgentApp, ...] = (
    AgentApp(
        "agent_pr_merge_unbound",
        (
            (
                "get_pull_request_status",
                lambda o: {"owner": "acme", "repo": "app", "pull_number": 7},
            ),
            ("merge_pull_request", lambda o: {"owner": "acme", "repo": "app", "pull_number": 7}),
        ),
        "candidate_risk",
    ),
    AgentApp(
        "agent_pr_merge_bound",
        (
            (
                "get_pull_request_status",
                lambda o: {"owner": "acme", "repo": "app", "pull_number": 7},
            ),
            (
                "merge_pull_request",
                lambda o: {
                    "owner": "acme",
                    "repo": "app",
                    "pull_number": 7,
                    "sha": _field(o, "get_pull_request_status", "head_sha"),
                },
            ),
        ),
        "protected",
    ),
    AgentApp(
        "agent_k8s_unbound",
        (
            ("get_deployment", lambda o: {"name": "api", "namespace": "prod"}),
            (
                "replace_deployment",
                lambda o: {"name": "api", "namespace": "prod", "body": {"replicas": 4}},
            ),
        ),
        "candidate_risk",
    ),
    AgentApp(
        "agent_k8s_bound",
        (
            ("get_deployment", lambda o: {"name": "api", "namespace": "prod"}),
            (
                "replace_deployment",
                lambda o: {
                    "name": "api",
                    "namespace": "prod",
                    "body": {"replicas": 4},
                    "resourceVersion": _field(o, "get_deployment", "resourceVersion"),
                },
            ),
        ),
        "protected",
    ),
    AgentApp(
        "agent_consul_unbound",
        (
            ("kv_get", lambda o: {"key": "service/web/weight"}),
            ("kv_put", lambda o: {"key": "service/web/weight", "value": "20"}),
        ),
        "candidate_risk",
    ),
    AgentApp(
        "agent_consul_cas",
        (
            ("kv_get", lambda o: {"key": "service/web/weight"}),
            (
                "kv_put",
                lambda o: {
                    "key": "service/web/weight",
                    "value": "20",
                    "cas": _field(o, "kv_get", "ModifyIndex"),
                },
            ),
        ),
        "protected",
    ),
    AgentApp(
        "agent_s3_two_objects",
        (
            # checks object A, but writes object B: no dependency
            ("head_object", lambda o: {"Bucket": "cfg", "Key": "a.json"}),
            ("put_object", lambda o: {"Bucket": "cfg", "Key": "b.json", "Body": "{}"}),
        ),
        "protected",
    ),
    AgentApp(
        "agent_file_write",
        (
            ("get_file_info", lambda o: {"path": "/srv/tmp/x"}),
            ("write_file", lambda o: {"path": "/srv/tmp/x", "content": ""}),
        ),
        "candidate_risk",
    ),
    AgentApp(
        "agent_payment",
        (
            ("retrieve_payment_intent", lambda o: {"id": "pi_9"}),
            ("capture_payment_intent", lambda o: {"id": "pi_9"}),
        ),
        "protected",
    ),
    AgentApp(
        "agent_research",
        (
            ("get_file_contents", lambda o: {"owner": "acme", "repo": "app", "path": "README.md"}),
            ("read_file", lambda o: {"path": "/docs/a.md"}),
            ("chat_post_message", lambda o: {"channel": "#team", "text": "summary"}),
        ),
        "protected",
    ),
)


def build_agent(app: AgentApp) -> Any:
    from langgraph.prebuilt import create_react_agent

    from examples.langgraph.tools import ALL_TOOLS

    model = ScriptedChatModel(policy=plan_policy(list(app.steps)))
    return create_react_agent(model, list(ALL_TOOLS))
