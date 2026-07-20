"""Validation helpers for BindBench family manifests."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from agentlint.benchmark.models import ScenarioFamily, ScenarioVariant, VariantKind

REQUIRED_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "family_id",
        "category",
        "title",
        "description",
        "resource",
        "variants",
    }
)
REQUIRED_VARIANT_FIELDS = frozenset(
    {
        "kind",
        "check_contract",
        "effect_contract",
        "expected_result",
        "mutation",
        "repair_obligation",
        "representations",
    }
)
REQUIRED_VARIANTS = frozenset(VariantKind)


class ManifestValidationError(ValueError):
    """Raised when a BindBench manifest violates the M1 corpus schema."""


def load_manifest(path: Path) -> ScenarioFamily:
    """Load and validate a JSON BindBench manifest from disk."""

    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ManifestValidationError("manifest document must be a JSON object")
    return validate_manifest(document)


def validate_manifest(document: Mapping[str, Any]) -> ScenarioFamily:
    """Validate a BindBench manifest and return its typed representation."""

    missing = sorted(REQUIRED_MANIFEST_FIELDS.difference(document))
    if missing:
        raise ManifestValidationError(f"manifest missing required field(s): {', '.join(missing)}")
    if document["schema_version"] != 1:
        raise ManifestValidationError("schema_version must be 1")

    variants = _variants(document["variants"])
    found_kinds = frozenset(variant.kind for variant in variants)
    if found_kinds != REQUIRED_VARIANTS:
        raise ManifestValidationError(
            "manifest must contain exactly vulnerable, repaired, and safe_near_miss variants"
        )

    return ScenarioFamily(
        family_id=_required_text(document, "family_id"),
        category=_required_text(document, "category"),
        title=_required_text(document, "title"),
        description=_required_text(document, "description"),
        resource=_required_text(document, "resource"),
        variants=variants,
    )


def _variants(value: object) -> tuple[ScenarioVariant, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ManifestValidationError("variants must be a list")
    if len(value) != 3:
        raise ManifestValidationError("variants must contain exactly three entries")

    variants: list[ScenarioVariant] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ManifestValidationError("variant entries must be objects")
        missing = sorted(REQUIRED_VARIANT_FIELDS.difference(item))
        if missing:
            raise ManifestValidationError(
                f"variant missing required field(s): {', '.join(missing)}"
            )
        variants.append(
            ScenarioVariant(
                kind=_variant_kind(_required_text(item, "kind")),
                check_contract=_required_text(item, "check_contract"),
                effect_contract=_required_text(item, "effect_contract"),
                expected_result=_required_text(item, "expected_result"),
                mutation=_required_text(item, "mutation"),
                repair_obligation=_required_text(item, "repair_obligation"),
                representations=_representations(item["representations"]),
            )
        )
    return tuple(variants)


def _required_text(document: Mapping[str, Any], field_name: str) -> str:
    value = document[field_name]
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(f"{field_name} must be a non-empty string")
    return value


def _variant_kind(value: str) -> VariantKind:
    try:
        return VariantKind(value)
    except ValueError as error:
        raise ManifestValidationError(f"unsupported variant kind: {value}") from error


def _representations(value: object) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence) or not value:
        raise ManifestValidationError("representations must be a non-empty list")
    representations = tuple(item for item in value if isinstance(item, str) and item.strip())
    if len(representations) != len(value):
        raise ManifestValidationError("representations entries must be non-empty strings")
    return representations
