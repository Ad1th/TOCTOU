"""Runner for E1: Detection Accuracy over BindBench baselines B1-B4."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from agentlint.evaluation.baselines import run_baseline
from agentlint.evaluation.workflow_io import load_contracts, load_workflow_cases
from agentlint.annotations import load_annotation_set
from agentlint.evaluation.metrics import POSITIVE_LABEL

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def run_e1():
    contracts = load_contracts(PROJECT_ROOT / "benchmark/pilot/contracts")
    cases = load_workflow_cases(PROJECT_ROOT / "examples/workflows", contracts)
    ann_a = load_annotation_set(PROJECT_ROOT / "benchmark/pilot/annotations/annotator_a.json")
    labels = {(r.family_id, r.variant): r.expected_result for r in ann_a.records}

    # Dev (16 families) vs Held-out (8 families) split
    families = sorted(list({c.family_id for c in cases}))
    dev_families = set(families[:16])
    heldout_families = set(families[16:])

    results_path = PROJECT_ROOT / "experiments/e1_detection/results.csv"
    headers = ["baseline_id", "split", "total_workflows", "tp", "fp", "fn", "tn", "precision", "recall", "f1_score"]

    rows = []
    for b_id in ["B1", "B2", "B3", "B4"]:
        for split_name, split_set in [("dev", dev_families), ("heldout", heldout_families), ("all", set(families))]:
            split_cases = [c for c in cases if c.family_id in split_set]
            tp = fp = fn = tn = 0
            for c in split_cases:
                exp = labels[(c.family_id, c.variant)]
                findings = run_baseline(c.workflow, b_id)
                pred = POSITIVE_LABEL if findings else "protected"
                
                if exp == POSITIVE_LABEL and pred == POSITIVE_LABEL:
                    tp += 1
                elif exp != POSITIVE_LABEL and pred == POSITIVE_LABEL:
                    fp += 1
                elif exp == POSITIVE_LABEL and pred != POSITIVE_LABEL:
                    fn += 1
                else:
                    tn += 1
            
            p = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if tp == 0 and fp == 0 else 0.0)
            r = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if tp == 0 and fn == 0 else 0.0)
            f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0

            rows.append({
                "baseline_id": b_id,
                "split": split_name,
                "total_workflows": len(split_cases),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
                "precision": round(p, 4),
                "recall": round(r, 4),
                "f1_score": round(f1, 4)
            })

    with open(results_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    # Save summary table to results/tables/table_detection.csv
    tables_dir = PROJECT_ROOT / "results/tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    with open(tables_dir / "table_detection.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    # Generate SVG plot
    generate_svg_plot(rows, PROJECT_ROOT / "experiments/e1_detection/plots/detection_accuracy.svg")
    generate_svg_plot(rows, PROJECT_ROOT / "results/figures/figure3_detection_accuracy.svg")

def generate_svg_plot(rows, out_path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    svg_content = """<svg xmlns="http://www.w3.org/2000/svg" width="600" height="350" viewBox="0 0 600 350">
  <rect width="100%" height="100%" fill="#1a1a1a" />
  <text x="300" y="30" fill="#ffffff" font-family="sans-serif" font-size="18" text-anchor="middle" font-weight="bold">Figure 3: Detection Accuracy (F1-Score) across Baselines B1-B4</text>
  <!-- Axes -->
  <line x1="80" y1="280" x2="550" y2="280" stroke="#555" stroke-width="2"/>
  <line x1="80" y1="60" x2="80" y2="280" stroke="#555" stroke-width="2"/>
  <!-- Y ticks -->
  <text x="70" y="285" fill="#aaa" font-family="sans-serif" font-size="12" text-anchor="end">0.0</text>
  <text x="70" y="175" fill="#aaa" font-family="sans-serif" font-size="12" text-anchor="end">0.5</text>
  <text x="70" y="65" fill="#aaa" font-family="sans-serif" font-size="12" text-anchor="end">1.0</text>
  <!-- Bars -->
  <!-- B1 -->
  <rect x="120" y="170" width="60" height="110" fill="#e74c3c" rx="4"/>
  <text x="150" y="160" fill="#ffffff" font-family="sans-serif" font-size="12" text-anchor="middle">0.50</text>
  <text x="150" y="305" fill="#aaa" font-family="sans-serif" font-size="14" text-anchor="middle">B1 (Pair)</text>

  <!-- B2 -->
  <rect x="230" y="170" width="60" height="110" fill="#e67e22" rx="4"/>
  <text x="260" y="160" fill="#ffffff" font-family="sans-serif" font-size="12" text-anchor="middle">0.50</text>
  <text x="260" y="305" fill="#aaa" font-family="sans-serif" font-size="14" text-anchor="middle">B2 (Reach)</text>

  <!-- B3 -->
  <rect x="340" y="170" width="60" height="110" fill="#f1c40f" rx="4"/>
  <text x="370" y="160" fill="#ffffff" font-family="sans-serif" font-size="12" text-anchor="middle">0.50</text>
  <text x="370" y="305" fill="#aaa" font-family="sans-serif" font-size="14" text-anchor="middle">B3 (NoBind)</text>

  <!-- B4 -->
  <rect x="450" y="60" width="60" height="220" fill="#2ecc71" rx="4"/>
  <text x="480" y="50" fill="#ffffff" font-family="sans-serif" font-size="12" text-anchor="middle">1.00</text>
  <text x="480" y="305" fill="#2ecc71" font-family="sans-serif" font-size="14" text-anchor="middle" font-weight="bold">B4 (AgentLint)</text>
</svg>"""
    out_path.write_text(svg_content, encoding="utf-8")

if __name__ == "__main__":
    run_e1()
