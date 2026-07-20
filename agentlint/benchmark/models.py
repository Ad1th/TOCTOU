"""Typed data model for BindBench family manifests."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class VariantKind(StrEnum):
    """The three required variants for every BindBench scenario family."""

    VULNERABLE = "vulnerable"
    REPAIRED = "repaired"
    SAFE_NEAR_MISS = "safe_near_miss"


@dataclass(frozen=True, slots=True)
class ScenarioVariant:
    """One labeled workflow variant in a BindBench family."""

    kind: VariantKind
    check_contract: str
    effect_contract: str
    expected_result: str
    mutation: str
    repair_obligation: str
    representations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScenarioFamily:
    """A BindBench family containing vulnerable, repaired, and safe-near-miss variants."""

    family_id: str
    category: str
    title: str
    description: str
    resource: str
    variants: tuple[ScenarioVariant, ...]
