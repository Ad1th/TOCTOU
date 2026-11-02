"""Turn revision results into paper figures (PDF) and LaTeX number macros.

Every number quoted in the revised manuscript is emitted here as a macro in
``paper/procedia/generated/results.tex``, so the text cannot drift from the results.
"""

from __future__ import annotations

import json
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from experiments.revision.common import FIGURES, GENERATED, RESULTS  # noqa: E402

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "STIXGeneral", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 8,
        "axes.titlesize": 8,
        "axes.labelsize": 8,
        "legend.fontsize": 7,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
    }
)
INK = "#1f2933"
PALETTE = ["#9aa5b1", "#7b8794", "#52606d", "#3e4c59", "#1f6feb"]


def _load(name: str) -> Any:
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def _pct(x: float) -> str:
    return f"{100 * x:.1f}\\%" if x not in (0.0, 1.0) else f"{int(100 * x)}\\%"


def _f3(x: float) -> str:
    return f"{x:.3f}" if x != 1.0 else "1.000"


def _ms(seconds: float) -> str:
    ms = seconds * 1000
    return f"{ms:.1f}" if ms < 100 else f"{ms:.0f}"


def macros() -> str:
    e1, e2, e3, e4, e5, e6 = (
        _load(f)
        for f in (
            "e1_bindbench.json",
            "e2_benign.json",
            "e3_contract_effort.json",
            "e4_langgraph.json",
            "e5_dynamic.json",
            "e6_scalability.json",
        )
    )
    m: dict[str, str] = {}
    letters = {"B1": "A", "B2": "B", "B3": "C", "B3A": "D", "B4": "E"}
    for bid, b in e1["baselines"].items():
        tag = letters[bid]
        c, met = b["counts"]["all"], b["metrics"]["all"]
        m[f"bb{tag}tp"], m[f"bb{tag}fp"], m[f"bb{tag}fn"] = str(c["tp"]), str(c["fp"]), str(c["fn"])
        m[f"bb{tag}p"], m[f"bb{tag}r"], m[f"bb{tag}f"] = (
            _f3(met["precision"]),
            _f3(met["recall"]),
            _f3(met["f1"]),
        )
        for origin in ("pilot", "extension"):
            mo = b["metrics"].get(origin, {"f1": 0.0})
            m[f"bb{tag}f{origin}"] = _f3(mo["f1"])
        m[f"bb{tag}nm"] = str(sum(b["fp_by_near_miss"].values()))
        m[f"bb{tag}rep"] = str(b["flagged_by_variant"].get("repaired", 0))
        m[f"bb{tag}missadv"] = str(b["missed_by_vuln_kind"].get("advisory", 0))
        m[f"bb{tag}missmis"] = str(b["missed_by_vuln_kind"].get("mis_scoped", 0))
        bn = e2["baselines"][bid]
        m[f"bn{tag}fp"] = str(bn["benign_fp_workflows"])
        m[f"bn{tag}fprate"] = _pct(bn["benign_fp_rate"])
        m[f"bn{tag}rec"] = _pct(bn["injected_recall"])
        m[f"bn{tag}exact"] = str(bn["injected_exactly_one_finding"])
        for p, rates in e2["single_pattern_fp_rate"].items():
            word = ["", "one", "two", "three", "four", "five", "six", "seven", "eight"][int(p[1])]
            m[f"sp{word}{tag}"] = _pct(rates[bid])
    m["bbWorkflows"], m["bbFamilies"] = str(e1["n_workflows"]), str(e1["n_families"])
    m["bnBenign"], m["bnInjected"] = str(e2["n_benign"]), str(e2["n_injected"])
    m["bnMedNodes"], m["bnMaxNodes"] = str(int(e2["nodes_median"])), str(e2["nodes_max"])
    m["bnCyclic"] = str(e2["cyclic_workflows"])
    # E3
    m["ceTools"], m["ceServices"] = str(e3["n_tools"]), str(e3["n_services"])
    m["ceLines"] = f"{e3['mean_json_lines']:.1f}"
    m["ceFields"] = f"{e3['mean_filled_fields']:.1f}"
    m["ceJudgement"] = str(e3["tools_needing_judgement"])
    m["ceFull"] = str(e3["fully_inferred_tools"])
    m["ceBound"], m["ceEnforced"], m["ceAdvisory"] = (
        str(e3["n_bound_effects"]),
        str(e3["n_enforced"]),
        str(e3["n_advisory"]),
    )
    ops = e3["operations"]
    m["ceRead"], m["ceCheck"], m["ceEffect"] = (
        str(ops.get("read", 0)),
        str(ops.get("check", 0)),
        str(ops.get("effect", 0)),
    )
    names = {
        "operation": "Op",
        "resource_argument": "Res",
        "version_argument": "Ver",
        "binding_mechanisms": "Mech",
        "authority_behavior": "Auth",
        "predicate": "Pred",
    }
    for k, v in e3["field_agreement_rate"].items():
        m[f"ce{names[k]}"] = _pct(v)
    bound = [
        t
        for t in e3["per_tool"]
        if t["judgement_fields"] and "authority_behavior" in t["judgement_fields"]
    ]
    m["ceAuthBound"] = str(sum(t["agreement"]["authority_behavior"] for t in bound))
    checks = [t for t in e3["per_tool"] if t["operation"] == "check"]
    m["ceOpCheck"] = str(sum(t["agreement"]["operation"] for t in checks))
    m["ceNChecks"] = str(len(checks))
    # E4
    m["lgApps"], m["lgStatic"], m["lgTrace"] = (
        str(e4["n_apps"]),
        str(e4["n_static"]),
        str(e4["n_trace"]),
    )
    m["lgAgree"], m["lgDyn"], m["lgRisky"] = (
        str(e4["label_agreement"]),
        str(e4["dynamic_agreement"]),
        str(e4["n_risky"]),
    )
    m["lgMaxMs"] = _ms(max(r["frontend_and_analysis_seconds"] for r in e4["rows"]))
    # E5
    for corpus, tag in (("bindbench_v2", "B"), ("benign_mix", "M")):
        d = e5[corpus]
        m[f"dy{tag}n"] = str(d["n"])
        m[f"dy{tag}static"] = _ms(d["static_seconds"])
        m[f"dy{tag}sys"] = _ms(d["systematic_seconds"])
        m[f"dy{tag}agree"] = str(d["systematic_agreement_with_static"])
        m[f"dy{tag}exec"] = f"{d['systematic_executions_total']:,}".replace(",", "{,}")
        m[f"dy{tag}execmax"] = f"{d['systematic_executions_max']:,}".replace(",", "{,}")
        m[f"dy{tag}fp"] = str(d["systematic_dynamic_false_positives"])
        budgets = d["random_budgets"]
        for p, curve in d["random_recall_curves"].items():
            pt = "lo" if p == "0.05" else "hi"
            for k, v in zip(budgets, curve, strict=True):
                m[f"dy{tag}{pt}k{_num(k)}"] = _pct(v)
    # E6
    v2 = [r for r in e6["rows"] if r["impl"] == "v2"]
    v1 = [r for r in e6["rows"] if r["impl"] == "v1"]
    for r in v2:
        if r["nodes"] in (10_000, 100_000):
            size = "tenk" if r["nodes"] == 10_000 else "hundredk"
            key = f"sc{r['topology'].replace('_', '')}{size}"
            m[key] = _ms(r["median_s"])
            m[key + "mem"] = f"{r['peak_mib']:.0f}"
            m[key + "edges"] = f"{r['edges']:,}".replace(",", "{,}")
            m[key + "find"] = f"{r['findings']:,}".replace(",", "{,}")
    for r in v1:
        if r["nodes"] == 1000:
            m["scVoneK"] = f"{r['median_s']:.1f}"
            m["scVtwoK"] = _ms(r["v2_median_s"])
            m["scVoneKfind"], m["scVtwoKfind"] = str(r["v1_findings"]), str(r["v2_findings"])
    m["scMaxEdges"] = f"{max(r['edges'] for r in v2):,}".replace(",", "{,}")
    return "\n".join(f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(m.items())) + "\n"


def _num(k: int) -> str:
    return {1: "one", 2: "two", 5: "five", 10: "ten", 20: "twenty", 50: "fifty", 100: "hundred"}[k]


def fig_baselines() -> None:
    e1, e2 = _load("e1_bindbench.json"), _load("e2_benign.json")
    ids = ["B1", "B2", "B3", "B3A", "B4"]
    labels = [
        "B1\nordered\npair",
        "B2\n+reach.\n+resource",
        "B3\n+binding\npresence",
        "B3A\n+authority",
        "B4\nours",
    ]
    fig, axes = plt.subplots(1, 2, figsize=(6.3, 2.1))
    width = 0.26
    xs = range(len(ids))
    for j, (metric, name) in enumerate(
        (("precision", "Precision"), ("recall", "Recall"), ("f1", "F1"))
    ):
        vals = [e1["baselines"][b]["metrics"]["all"][metric] for b in ids]
        axes[0].bar(
            [x + (j - 1) * width for x in xs],
            vals,
            width,
            label=name,
            color=["#bcccdc", "#627d98", "#102a43"][j],
        )
    axes[0].set_xticks(list(xs), labels)
    axes[0].set_ylim(0, 1.32)
    axes[0].set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    axes[0].set_ylabel("Score")
    axes[0].set_title(f"(a) BindBench v2 ({e1['n_workflows']} workflows)")
    axes[0].legend(frameon=False, ncol=3, loc="upper left", bbox_to_anchor=(0, 1.02))
    fp = [e2["baselines"][b]["benign_fp_rate"] for b in ids]
    rec = [e2["baselines"][b]["injected_recall"] for b in ids]
    axes[1].bar([x - width / 2 for x in xs], fp, width, label="FP rate (benign)", color="#d9822b")
    for x, v in zip(xs, fp, strict=True):
        if v == 0:
            axes[1].text(
                x - width / 2, 0.02, "0", ha="center", va="bottom", fontsize=6, color="#d9822b"
            )
    axes[1].bar([x + width / 2 for x in xs], rec, width, label="Recall (injected)", color="#102a43")
    axes[1].set_xticks(list(xs), labels)
    axes[1].set_ylim(0, 1.32)
    axes[1].set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    axes[1].set_ylabel("Rate")
    axes[1].set_title(
        f"(b) Tool-library mix ({e2['n_benign']} benign + {e2['n_injected']} injected)"
    )
    axes[1].legend(frameon=False, ncol=2, loc="upper left", bbox_to_anchor=(0, 1.02))
    for ax in axes:
        ax.tick_params(axis="x", length=0)
    fig.tight_layout(w_pad=1.5)
    fig.savefig(FIGURES / "fig_baselines.pdf")
    plt.close(fig)


def fig_dynamic() -> None:
    e5 = _load("e5_dynamic.json")
    fig, ax = plt.subplots(figsize=(3.1, 2.0))
    styles = {
        ("bindbench_v2", "0.05"): ("#627d98", "--"),
        ("bindbench_v2", "0.2"): ("#627d98", "-"),
        ("benign_mix", "0.05"): ("#d9822b", "--"),
        ("benign_mix", "0.2"): ("#d9822b", "-"),
    }
    names = {"bindbench_v2": "BindBench", "benign_mix": "Tool mix"}
    for corpus in ("bindbench_v2", "benign_mix"):
        d = e5[corpus]
        for p, curve in d["random_recall_curves"].items():
            color, ls = styles[(corpus, p)]
            ax.plot(
                d["random_budgets"],
                curve,
                ls,
                color=color,
                marker="o",
                ms=2.5,
                label=f"{names[corpus]}, $p$={p}",
            )
    ax.axhline(1.0, color=INK, lw=0.8, ls=":")
    ax.text(1.05, 1.03, "Static analysis (one pass)", fontsize=6.5, color=INK, va="bottom")
    ax.set_xscale("log")
    ax.set_xlabel("Random schedules executed per workflow")
    ax.set_ylabel("Recall on risky workflows")
    ax.set_ylim(0, 1.12)
    ax.legend(frameon=False, loc="lower right", handlelength=3.2)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig_dynamic.pdf")
    plt.close(fig)


def fig_scalability() -> None:
    e6 = _load("e6_scalability.json")
    fig, ax = plt.subplots(figsize=(3.1, 2.0))
    colors = {
        "chain": "#9aa5b1",
        "layered": "#627d98",
        "random_dag": "#102a43",
        "cyclic": "#d9822b",
    }
    labels = {
        "chain": "chain",
        "layered": "layered DAG",
        "random_dag": "dense DAG",
        "cyclic": "cyclic",
    }
    markers = {"chain": "s", "layered": "o", "random_dag": "^", "cyclic": "D"}
    for topo, color in colors.items():
        rows = [r for r in e6["rows"] if r["impl"] == "v2" and r["topology"] == topo]
        ax.plot(
            [r["nodes"] for r in rows],
            [r["median_s"] for r in rows],
            "-",
            marker=markers[topo],
            ms=3,
            color=color,
            label=f"v2, {labels[topo]}",
        )
    v1 = [r for r in e6["rows"] if r["impl"] == "v1"]
    ax.plot(
        [r["nodes"] for r in v1],
        [r["median_s"] for r in v1],
        "x--",
        ms=3.5,
        color="#ba2525",
        label="v1 (submitted), layered",
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Workflow nodes $N$")
    ax.set_ylabel("Median analysis time (s)")
    ax.legend(frameon=False, fontsize=6, loc="upper center", bbox_to_anchor=(0.45, -0.42), ncol=2)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig_scalability.pdf", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    GENERATED.mkdir(parents=True, exist_ok=True)
    (GENERATED / "results.tex").write_text(
        "% generated by experiments/revision/make_paper_assets.py -- do not edit\n" + macros(),
        encoding="utf-8",
    )
    fig_baselines()
    fig_dynamic()
    fig_scalability()


if __name__ == "__main__":
    main()
