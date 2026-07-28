"""Metric computation for AgentLint evaluation runs."""

from __future__ import annotations

from agentlint.evaluation.models import EvaluationMetrics, WorkflowResult

POSITIVE_LABEL = "candidate_risk"


def compute_metrics(results: tuple[WorkflowResult, ...]) -> EvaluationMetrics:
    """Compute binary detection metrics from analyzer outputs and ground truth."""

    true_positives = sum(
        1
        for result in results
        if result.expected_label == POSITIVE_LABEL and result.predicted_label == POSITIVE_LABEL
    )
    false_positives = sum(
        1
        for result in results
        if result.expected_label != POSITIVE_LABEL and result.predicted_label == POSITIVE_LABEL
    )
    false_negatives = sum(
        1
        for result in results
        if result.expected_label == POSITIVE_LABEL and result.predicted_label != POSITIVE_LABEL
    )
    precision = _ratio(true_positives, true_positives + false_positives)
    recall = _ratio(true_positives, true_positives + false_negatives)
    f1_score = _ratio(2 * precision * recall, precision + recall)

    return EvaluationMetrics(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1_score=f1_score,
        total_workflows_analyzed=len(results),
        total_findings=sum(result.finding_count for result in results),
        total_runtime_seconds=sum(result.runtime_seconds for result in results),
    )


def _ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
