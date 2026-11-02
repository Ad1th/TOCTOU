"""E3: contract-authoring effort on real tool APIs and schema-based draft inference."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from agentlint.benchmark.tool_catalog import CATALOG, write_catalog
from agentlint.contracts.infer import INFERRED_FIELDS, field_agreement, infer_contract
from agentlint.contracts.validation import validate_contract
from experiments.revision.common import ROOT, write_json


def run() -> dict[str, Any]:
    write_catalog(ROOT / "benchmark" / "tools")
    per_tool = []
    agree: Counter[str] = Counter()
    ops: Counter[str] = Counter()
    for tool in CATALOG:
        contract = tool["contract"]
        validate_contract(contract)  # every hand-written contract must pass the schema
        draft = infer_contract(tool["name"], tool["parameters"], tool["required"])
        fa = field_agreement(draft, contract)
        agree.update(k for k, v in fa.items() if v)
        ops[contract["operation"]] += 1
        text = json.dumps(contract, indent=2, sort_keys=True)
        judgement_fields = []
        if contract["operation"] == "check":
            judgement_fields.append("predicate")
        if contract["binding_mechanisms"] != ["none"]:
            judgement_fields.append("authority_behavior")
        per_tool.append(
            {
                "tool": f"{tool['service']}.{tool['name']}",
                "operation": contract["operation"],
                "json_lines": text.count("\n") + 1,
                "filled_fields": sum(v is not None for v in contract.values())
                - 1,  # minus schema_version
                "judgement_fields": judgement_fields,
                "draft_correct_fields": sum(fa.values()),
                "agreement": fa,
            }
        )
    n = len(CATALOG)
    bound = [t for t in CATALOG if t["contract"]["binding_mechanisms"] != ["none"]]
    out = {
        "n_tools": n,
        "n_services": len({t["service"] for t in CATALOG}),
        "operations": dict(ops),
        "mean_json_lines": sum(t["json_lines"] for t in per_tool) / n,
        "mean_filled_fields": sum(t["filled_fields"] for t in per_tool) / n,
        "field_agreement_rate": {f: agree[f] / n for f in INFERRED_FIELDS},
        "fully_inferred_tools": sum(
            t["draft_correct_fields"] == len(INFERRED_FIELDS) for t in per_tool
        ),
        "tools_needing_judgement": sum(bool(t["judgement_fields"]) for t in per_tool),
        "n_bound_effects": len(bound),
        "n_enforced": sum(t["contract"]["authority_behavior"] == "enforced" for t in bound),
        "n_advisory": sum(t["contract"]["authority_behavior"] == "advisory" for t in bound),
        "per_tool": per_tool,
    }
    write_json("e3_contract_effort.json", out)
    return out


if __name__ == "__main__":
    r = run()
    print({k: v for k, v in r.items() if k != "per_tool"})
    for t in r["per_tool"]:
        bad = [k for k, v in t["agreement"].items() if not v]
        if bad:
            print(t["tool"], bad)
