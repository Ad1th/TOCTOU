"""E4: AgentLint on executable LangGraph applications (static and trace frontends)."""

from __future__ import annotations

import time
import warnings
from typing import Any

from agentlint.frontends.langgraph import workflow_from_messages, workflow_from_state_graph
from agentlint.ir.findings import generate_findings
from experiments.revision.common import write_json

warnings.filterwarnings("ignore")


def _execute_graph(app: Any, adversarial: bool) -> dict[str, Any]:
    from examples.langgraph.tools import BACKEND

    BACKEND.reset()
    if adversarial:
        BACKEND.adversary = BACKEND.mutate
    error = None
    try:
        app.build().compile().invoke(dict(app.state))
    except Exception as exc:  # a rejected stale effect surfaces as a ToolException
        error = type(exc).__name__
    return {
        "violations": list(BACKEND.violations),
        "rejected": list(BACKEND.rejected),
        "error": error,
    }


def _execute_agent(app: Any, adversarial: bool) -> tuple[list[Any], dict[str, Any]]:
    from examples.langgraph.apps import build_agent
    from examples.langgraph.tools import BACKEND

    BACKEND.reset()
    if adversarial:
        BACKEND.adversary = BACKEND.mutate
    result = build_agent(app).invoke({"messages": [("user", "perform the task")]})
    return result["messages"], {
        "violations": list(BACKEND.violations),
        "rejected": list(BACKEND.rejected),
    }


def run() -> dict[str, Any]:
    from examples.langgraph.apps import AGENT_APPS, GRAPH_APPS
    from examples.langgraph.tools import registry

    reg = registry()
    rows: list[dict[str, Any]] = []
    for app in GRAPH_APPS:
        t0 = time.perf_counter()
        wf = workflow_from_state_graph(app.name, app.build(), reg)
        findings = generate_findings(wf)
        elapsed = time.perf_counter() - t0
        benign = _execute_graph(app, adversarial=False)
        adv = _execute_graph(app, adversarial=True)
        rows.append(
            {
                "app": app.name,
                "frontend": "static (StateGraph AST)",
                "expected": app.expected,
                "predicted": "candidate_risk" if findings else "protected",
                "n_nodes": len(wf.nodes),
                "n_tool_nodes": sum(n.contract is not None for n in wf.nodes),
                "findings": [
                    (f.check_node_id, f.effect_node_id, f.resource.resource_id) for f in findings
                ],
                "benign_run_violations": len(benign["violations"]),
                "adversarial_violations": len(adv["violations"]),
                "adversarial_rejections": len(adv["rejected"]),
                "frontend_and_analysis_seconds": elapsed,
            }
        )
    for agent_app in AGENT_APPS:
        messages, benign = _execute_agent(agent_app, adversarial=False)
        _, adv = _execute_agent(agent_app, adversarial=True)
        t0 = time.perf_counter()
        wf = workflow_from_messages(agent_app.name, messages, reg)
        findings = generate_findings(wf)
        elapsed = time.perf_counter() - t0
        rows.append(
            {
                "app": agent_app.name,
                "frontend": "trace (create_react_agent)",
                "expected": agent_app.expected,
                "predicted": "candidate_risk" if findings else "protected",
                "n_nodes": len(wf.nodes),
                "n_tool_nodes": sum(n.contract is not None for n in wf.nodes),
                "findings": [
                    (f.check_node_id, f.effect_node_id, f.resource.resource_id) for f in findings
                ],
                "benign_run_violations": len(benign["violations"]),
                "adversarial_violations": len(adv["violations"]),
                "adversarial_rejections": len(adv["rejected"]),
                "frontend_and_analysis_seconds": elapsed,
            }
        )
    correct = sum(r["expected"] == r["predicted"] for r in rows)
    confirmed = sum(
        (r["predicted"] == "candidate_risk") == (int(r["adversarial_violations"]) > 0) for r in rows
    )
    out = {
        "n_apps": len(rows),
        "n_static": len(GRAPH_APPS),
        "n_trace": len(AGENT_APPS),
        "label_agreement": correct,
        "dynamic_agreement": confirmed,
        "n_risky": sum(r["expected"] == "candidate_risk" for r in rows),
        "rows": rows,
    }
    write_json("e4_langgraph.json", out)
    return out


if __name__ == "__main__":
    r = run()
    for row in r["rows"]:
        print(
            f"{row['app']:28s} exp={row['expected']:15s} pred={row['predicted']:15s} "
            f"nodes={row['n_nodes']} adv_viol={row['adversarial_violations']} "
            f"rej={row['adversarial_rejections']} benign_viol={row['benign_run_violations']} "
            f"{row['findings']}"
        )
    print({k: v for k, v in r.items() if k != "rows"})
