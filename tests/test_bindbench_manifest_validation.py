"""Tests for M1 BindBench pilot manifest validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentlint.benchmark import (
    ManifestValidationError,
    VariantKind,
    load_manifest,
    validate_manifest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_six_pilot_families_validate() -> None:
    """M1 includes one valid pilot family per frozen category."""

    manifests = [
        load_manifest(manifest_path)
        for manifest_path in sorted((PROJECT_ROOT / "benchmark/pilot/families").glob("*.json"))
    ]

    assert len(manifests) == 6
    assert {manifest.category for manifest in manifests} == {
        "file/object identity",
        "versioned key-value state",
        "HTTP-like resources",
        "authorization",
        "value/availability",
        "workflow control",
    }
    for manifest in manifests:
        assert {variant.kind for variant in manifest.variants} == set(VariantKind)


def test_manifest_validator_rejects_incomplete_variant_set() -> None:
    """Manifest validation enforces the three-variant BindBench family shape."""

    malformed_manifest = {
        "schema_version": 1,
        "family_id": "bad_family",
        "category": "workflow control",
        "title": "bad",
        "description": "bad",
        "resource": "task_id",
        "variants": [
            {
                "kind": "vulnerable",
                "check_contract": "check",
                "effect_contract": "effect",
                "expected_result": "candidate_risk",
                "mutation": "mutate",
                "repair_obligation": "repair",
                "representations": ["langgraph_source"],
            }
        ],
    }

    with pytest.raises(ManifestValidationError):
        validate_manifest(malformed_manifest)
