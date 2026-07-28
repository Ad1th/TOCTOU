"""Typed models for AgentLint evaluation artifacts."""

from __future__ import annotations

from dataclasses import dataclass

from agentlint.ir import Finding, Workflow


@dataclass(frozen=True, slots=True)
class WorkflowCase:
    """A benchmark workflow with corpus identity metadata."""

    workflow_id: str
    family_id: str
    variant: str
    workflow: Workflow


@dataclass(frozen=True, slots=True)
class WorkflowResult:
    """Analyzer output and label comparison for one workflow."""

    workflow_id: str
    family_id: str
    variant: str
    expected_label: str
    predicted_label: str
    finding_count: int
    runtime_seconds: float
    findings: tuple[Finding, ...]


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    """Aggregate binary classification and runtime metrics."""

    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    total_workflows_analyzed: int
    total_findings: int
    total_runtime_seconds: float
