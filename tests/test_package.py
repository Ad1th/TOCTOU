"""Tests for M0 package metadata."""

from agentlint import __version__


def test_version_is_declared() -> None:
    """The package exposes the version configured for the foundation release."""
    assert __version__ == "0.1.0"
