"""Typed data model for explicit AgentLint tool contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ToolOperation(StrEnum):
    """Supported operation classes for contracted tools."""

    READ = "read"
    CHECK = "check"
    EFFECT = "effect"
    WRITE = "write"


class BindingMechanism(StrEnum):
    """Modeled mechanisms that can bind a prior check to a later effect."""

    NONE = "none"
    ATOMIC = "atomic"
    VERSION = "version"
    STABLE_IDENTITY = "stable_identity"
    REVALIDATION = "revalidation"
    SYNCHRONIZATION = "synchronization"


class AuthorityBehavior(StrEnum):
    """Whether the resource authority enforces the declared binding."""

    ENFORCED = "enforced"
    ADVISORY = "advisory"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ToolContract:
    """Explicit semantics for one supported tool call."""

    contract_id: str
    operation: ToolOperation
    resource_argument: str
    predicate: str | None
    binding_mechanisms: tuple[BindingMechanism, ...]
    authority_behavior: AuthorityBehavior
    version_argument: str | None = None
    effect_category: str | None = None
    safety_oracle: str | None = None
