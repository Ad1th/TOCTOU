"""Integration tests for the AgentLint evaluation pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from agentlint.evaluation.metrics import compute_metrics
from agentlint.evaluation.models import WorkflowResult
from agentlint.evaluation.runner import run_evaluation
from agentlint.evaluation.workflow_io import load_contracts, load_workflow_cases

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class StepClock:
    """Deterministic clock for evaluation artifact tests."""

    def __init__(self) -> None:
        self._value = 0.0

    def __call__(self) -> float:
        current_value = self._value
        self._value += 0.001
        return current_value


def test_complete_evaluation_pipeline_writes_expected_artifacts(tmp_path: Path) -> None:
    """The default BindBench v2 workflows run end-to-end and produce evaluation artifacts."""

    metrics = run_evaluation(results_dir=tmp_path, clock=StepClock())

    assert metrics.total_workflows_analyzed == 120
    assert metrics.total_findings == 40
    assert metrics.true_positives == 40
    assert metrics.false_positives == 0
    assert metrics.false_negatives == 0
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1_score == 1.0
    assert (tmp_path / "findings").is_dir()
    assert (tmp_path / "metrics/summary.json").is_file()
    assert (tmp_path / "metrics/summary.csv").is_file()
    assert (tmp_path / "tables/summary.csv").is_file()
    assert (tmp_path / "figures/README.md").is_file()
    assert (tmp_path / "logs/experiment.log").is_file()


def test_finding_export_contains_structured_json(tmp_path: Path) -> None:
    """Finding exports are machine-readable and include required finding fields."""

    run_evaluation(results_dir=tmp_path, clock=StepClock())

    finding_payload = json.loads(
        (tmp_path / "findings/bb_kv_version_vulnerable.json").read_text(encoding="utf-8")
    )

    assert finding_payload["workflow_id"] == "bb_kv_version_vulnerable"
    assert finding_payload["expected_label"] == "candidate_risk"
    assert finding_payload["predicted_label"] == "candidate_risk"
    assert finding_payload["finding_count"] == 1
    assert finding_payload["findings"][0]["check_node_id"] == "check"
    assert finding_payload["findings"][0]["effect_node_id"] == "effect"
    assert finding_payload["findings"][0]["missing_binding"] == (
        "authority_enforced_check_effect_binding"
    )


def test_metric_computation_uses_actual_workflow_results() -> None:
    """Metric computation is derived from supplied result labels and findings."""

    results = (
        WorkflowResult(
            workflow_id="tp",
            family_id="f1",
            variant="vulnerable",
            expected_label="candidate_risk",
            predicted_label="candidate_risk",
            finding_count=1,
            runtime_seconds=0.1,
            findings=(),
        ),
        WorkflowResult(
            workflow_id="fp",
            family_id="f2",
            variant="repaired",
            expected_label="protected",
            predicted_label="candidate_risk",
            finding_count=1,
            runtime_seconds=0.2,
            findings=(),
        ),
        WorkflowResult(
            workflow_id="fn",
            family_id="f3",
            variant="vulnerable",
            expected_label="candidate_risk",
            predicted_label="protected",
            finding_count=0,
            runtime_seconds=0.3,
            findings=(),
        ),
    )

    metrics = compute_metrics(results)

    assert metrics.true_positives == 1
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5
    assert metrics.f1_score == 0.5
    assert metrics.total_runtime_seconds == 0.6


def test_evaluation_outputs_are_deterministic_with_fixed_clock(tmp_path: Path) -> None:
    """Fixed-clock runs produce byte-identical summaries and exported findings."""

    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"

    run_evaluation(results_dir=first_dir, clock=StepClock())
    run_evaluation(results_dir=second_dir, clock=StepClock())

    relative_paths = (
        "metrics/summary.json",
        "metrics/summary.csv",
        "tables/summary.csv",
        "logs/experiment.log",
        "findings/bb_file_identity_vulnerable.json",
        "findings/bb_file_identity_repaired.json",
    )
    for relative_path in relative_paths:
        assert (first_dir / relative_path).read_text(encoding="utf-8") == (
            second_dir / relative_path
        ).read_text(encoding="utf-8")


def test_default_workflow_fixtures_load_all_pilot_cases() -> None:
    """The evaluation fixtures cover every pilot annotation case."""

    contracts = load_contracts(PROJECT_ROOT / "benchmark/bindbench/contracts")
    cases = load_workflow_cases(PROJECT_ROOT / "benchmark/bindbench/workflows", contracts)

    assert len(cases) == 120
    assert sorted({case.variant for case in cases}) == ["repaired", "safe_near_miss", "vulnerable"]


def test_committed_bindbench_matches_generator(tmp_path: Path) -> None:
    """The corpus on disk is exactly what the declarative generator produces."""

    from agentlint.benchmark.bindbench import build

    build(tmp_path)
    for generated in sorted(tmp_path.rglob("*.json")):
        committed = PROJECT_ROOT / "benchmark/bindbench" / generated.relative_to(tmp_path)
        assert committed.read_text(encoding="utf-8") == generated.read_text(encoding="utf-8")
