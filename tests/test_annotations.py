"""Tests for M1 pilot annotation agreement."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentlint.annotations import AnnotationValidationError, cohen_kappa, load_annotation_set

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_two_pilot_annotation_sets_meet_kappa_threshold() -> None:
    """M1 pilot annotations meet the frozen kappa acceptance threshold."""

    annotations_dir = PROJECT_ROOT / "benchmark/pilot/annotations"
    annotator_a = load_annotation_set(annotations_dir / "annotator_a.json")
    annotator_b = load_annotation_set(annotations_dir / "annotator_b.json")

    assert annotator_a.annotator_id == "annotator_a"
    assert annotator_b.annotator_id == "annotator_b"
    assert len(annotator_a.records) == 18
    assert cohen_kappa(annotator_a, annotator_b) >= 0.70


def test_kappa_rejects_unpaired_annotation_sets() -> None:
    """Agreement calculation requires identical family/variant coverage."""

    annotations_dir = PROJECT_ROOT / "benchmark/pilot/annotations"
    annotator_a = load_annotation_set(annotations_dir / "annotator_a.json")
    annotator_b = load_annotation_set(annotations_dir / "annotator_b.json")
    truncated = type(annotator_b)(
        annotator_id=annotator_b.annotator_id,
        records=annotator_b.records[:-1],
    )

    with pytest.raises(AnnotationValidationError):
        cohen_kappa(annotator_a, truncated)
