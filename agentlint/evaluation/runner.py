"""Run AgentLint evaluation over local workflow fixtures."""

from __future__ import annotations

import argparse
import csv
import json
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

from agentlint.annotations import load_annotation_set
from agentlint.evaluation.metrics import POSITIVE_LABEL, compute_metrics
from agentlint.evaluation.models import EvaluationMetrics, WorkflowResult
from agentlint.evaluation.workflow_io import load_contracts, load_workflow_cases
from agentlint.ir import Finding, generate_findings

Clock = Callable[[], float]


def run_evaluation(
    *,
    workflows_path: Path = Path("benchmark/bindbench/workflows"),
    contracts_dir: Path = Path("benchmark/bindbench/contracts"),
    annotations_path: Path = Path("benchmark/bindbench/annotations/construction_labels.json"),
    results_dir: Path = Path("results"),
    clock: Clock = time.perf_counter,
) -> EvaluationMetrics:
    """Run the existing analyzer over workflow fixtures and write evaluation artifacts."""

    output_dirs = _prepare_output_dirs(results_dir)
    contracts = load_contracts(contracts_dir)
    cases = load_workflow_cases(workflows_path, contracts)
    labels = _ground_truth_labels(annotations_path)

    results: list[WorkflowResult] = []
    for case in cases:
        expected_label = labels[(case.family_id, case.variant)]
        started_at = clock()
        findings = generate_findings(case.workflow)
        finished_at = clock()
        results.append(
            WorkflowResult(
                workflow_id=case.workflow_id,
                family_id=case.family_id,
                variant=case.variant,
                expected_label=expected_label,
                predicted_label=POSITIVE_LABEL if findings else "protected",
                finding_count=len(findings),
                runtime_seconds=max(0.0, finished_at - started_at),
                findings=findings,
            )
        )

    ordered_results = tuple(sorted(results, key=lambda result: result.workflow_id))
    metrics = compute_metrics(ordered_results)
    _write_findings(output_dirs["findings"], ordered_results)
    _write_metrics(output_dirs["metrics"], metrics)
    _write_table(output_dirs["tables"], ordered_results)
    _write_figure_placeholder(output_dirs["figures"])
    _write_log(output_dirs["logs"], ordered_results, metrics)
    return metrics


def build_parser() -> argparse.ArgumentParser:
    """Create the evaluation command parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflows", type=Path, default=Path("benchmark/bindbench/workflows"))
    parser.add_argument("--contracts", type=Path, default=Path("benchmark/bindbench/contracts"))
    parser.add_argument(
        "--annotations",
        type=Path,
        default=Path("benchmark/bindbench/annotations/construction_labels.json"),
    )
    parser.add_argument("--results", type=Path, default=Path("results"))
    return parser


def main() -> int:
    """Run the command-line evaluation entry point."""

    args = build_parser().parse_args()
    run_evaluation(
        workflows_path=args.workflows,
        contracts_dir=args.contracts,
        annotations_path=args.annotations,
        results_dir=args.results,
    )
    return 0


def _prepare_output_dirs(results_dir: Path) -> dict[str, Path]:
    output_dirs = {
        "findings": results_dir / "findings",
        "metrics": results_dir / "metrics",
        "tables": results_dir / "tables",
        "figures": results_dir / "figures",
        "logs": results_dir / "logs",
    }
    for output_dir in output_dirs.values():
        output_dir.mkdir(parents=True, exist_ok=True)
    return output_dirs


def _ground_truth_labels(annotations_path: Path) -> dict[tuple[str, str], str]:
    annotations = load_annotation_set(annotations_path)
    return {
        (record.family_id, record.variant): record.expected_result for record in annotations.records
    }


def _write_findings(findings_dir: Path, results: tuple[WorkflowResult, ...]) -> None:
    for result in results:
        payload = {
            "workflow_id": result.workflow_id,
            "family_id": result.family_id,
            "variant": result.variant,
            "expected_label": result.expected_label,
            "predicted_label": result.predicted_label,
            "finding_count": result.finding_count,
            "findings": [_finding_to_json(finding) for finding in result.findings],
        }
        _write_json(findings_dir / f"{result.workflow_id}.json", payload)


def _write_metrics(metrics_dir: Path, metrics: EvaluationMetrics) -> None:
    payload = asdict(metrics)
    _write_json(metrics_dir / "summary.json", payload)
    with (metrics_dir / "summary.csv").open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=tuple(payload))
        writer.writeheader()
        writer.writerow(payload)


def _write_table(tables_dir: Path, results: tuple[WorkflowResult, ...]) -> None:
    with (tables_dir / "summary.csv").open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=(
                "workflow",
                "expected_label",
                "predicted_label",
                "finding_count",
                "runtime_seconds",
            ),
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "workflow": result.workflow_id,
                    "expected_label": result.expected_label,
                    "predicted_label": result.predicted_label,
                    "finding_count": result.finding_count,
                    "runtime_seconds": f"{result.runtime_seconds:.9f}",
                }
            )


def _write_figure_placeholder(figures_dir: Path) -> None:
    (figures_dir / "README.md").write_text(
        "# Figures\n\n"
        "No figures are generated by the current evaluation infrastructure. "
        "This directory is reserved for future automatically generated plots.\n",
        encoding="utf-8",
    )


def _write_log(
    logs_dir: Path,
    results: tuple[WorkflowResult, ...],
    metrics: EvaluationMetrics,
) -> None:
    lines = ["event,workflow_id,finding_count,runtime_seconds"]
    for result in results:
        lines.append(
            "workflow_analyzed,"
            f"{result.workflow_id},{result.finding_count},{result.runtime_seconds:.9f}"
        )
    lines.append(
        "evaluation_complete," f"ALL,{metrics.total_findings},{metrics.total_runtime_seconds:.9f}"
    )
    (logs_dir / "experiment.log").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _finding_to_json(finding: Finding) -> dict[str, Any]:
    return {
        "finding_id": finding.finding_id,
        "kind": finding.kind.value,
        "resource": {
            "resource_id": finding.resource.resource_id,
            "argument_name": finding.resource.argument_name,
            "resource_type": finding.resource.resource_type.value,
            "identity": finding.resource.identity,
        },
        "check_node_id": finding.check_node_id,
        "effect_node_id": finding.effect_node_id,
        "missing_binding": finding.missing_binding.value,
        "location": {
            "workflow_id": finding.location.workflow_id,
            "node_id": finding.location.node_id,
            "edge_id": finding.location.edge_id,
            "source": finding.location.source,
        },
        "repair_obligation_id": finding.repair_obligation_id.value,
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
