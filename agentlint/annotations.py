"""Annotation records and agreement metrics for M1 pilot labeling."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class AnnotationValidationError(ValueError):
    """Raised when a pilot annotation file is malformed."""


@dataclass(frozen=True, slots=True)
class AnnotationRecord:
    """One pilot annotation for a family variant."""

    family_id: str
    variant: str
    resource: str
    check: str
    effect: str
    mutation: str
    existing_binding: str
    expected_result: str
    repair_obligation: str

    @property
    def key(self) -> tuple[str, str]:
        """Stable record key for agreement calculations."""

        return (self.family_id, self.variant)


@dataclass(frozen=True, slots=True)
class AnnotationSet:
    """Annotations completed by one annotator."""

    annotator_id: str
    records: tuple[AnnotationRecord, ...]


def load_annotation_set(path: Path) -> AnnotationSet:
    """Load and validate an annotation set from JSON."""

    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise AnnotationValidationError("annotation document must be an object")
    return validate_annotation_set(document)


def validate_annotation_set(document: Mapping[str, Any]) -> AnnotationSet:
    """Validate an annotation document."""

    annotator_id = _required_text(document, "annotator_id")
    records_value = document.get("records")
    if isinstance(records_value, str) or not isinstance(records_value, Sequence):
        raise AnnotationValidationError("records must be a list")
    if not records_value:
        raise AnnotationValidationError("records must be non-empty")

    records = tuple(_record(record) for record in records_value)
    keys = [record.key for record in records]
    if len(keys) != len(set(keys)):
        raise AnnotationValidationError("records must not contain duplicate family/variant keys")
    return AnnotationSet(annotator_id=annotator_id, records=records)


def cohen_kappa(left: AnnotationSet, right: AnnotationSet) -> float:
    """Compute Cohen's kappa over expected-result labels for paired annotations."""

    left_labels = {record.key: record.expected_result for record in left.records}
    right_labels = {record.key: record.expected_result for record in right.records}
    if left_labels.keys() != right_labels.keys():
        raise AnnotationValidationError("annotation sets must cover the same records")

    keys = sorted(left_labels)
    total = len(keys)
    observed_agreement = sum(1 for key in keys if left_labels[key] == right_labels[key]) / total

    left_counts = Counter(left_labels.values())
    right_counts = Counter(right_labels.values())
    expected_agreement = sum(
        (left_counts[label] / total) * (right_counts[label] / total)
        for label in set(left_counts).union(right_counts)
    )
    if expected_agreement == 1.0:
        return 1.0 if observed_agreement == 1.0 else 0.0
    return (observed_agreement - expected_agreement) / (1.0 - expected_agreement)


def _record(value: object) -> AnnotationRecord:
    if not isinstance(value, Mapping):
        raise AnnotationValidationError("annotation records must be objects")
    return AnnotationRecord(
        family_id=_required_text(value, "family_id"),
        variant=_required_text(value, "variant"),
        resource=_required_text(value, "resource"),
        check=_required_text(value, "check"),
        effect=_required_text(value, "effect"),
        mutation=_required_text(value, "mutation"),
        existing_binding=_required_text(value, "existing_binding"),
        expected_result=_required_text(value, "expected_result"),
        repair_obligation=_required_text(value, "repair_obligation"),
    )


def _required_text(document: Mapping[str, Any], field_name: str) -> str:
    value = document.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise AnnotationValidationError(f"{field_name} must be a non-empty string")
    return value
