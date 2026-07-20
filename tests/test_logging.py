"""Tests for structured logging foundation utilities."""

from __future__ import annotations

import json
import logging

from agentlint.logging import JsonFormatter, configure_json_logger


def test_json_formatter_includes_extra_fields() -> None:
    """Structured logs retain declared fields in machine-readable JSON."""
    formatter = JsonFormatter()
    record = logging.makeLogRecord(
        {
            "name": "agentlint.test",
            "levelno": logging.INFO,
            "levelname": "INFO",
            "msg": "foundation_ready",
            "args": (),
            "milestone": "M0",
        }
    )

    payload = json.loads(formatter.format(record))

    assert payload["logger"] == "agentlint.test"
    assert payload["message"] == "foundation_ready"
    assert payload["milestone"] == "M0"
    assert payload["level"] == "INFO"


def test_configure_json_logger_is_idempotent() -> None:
    """Repeated setup does not duplicate handlers for the same logger."""
    logger = configure_json_logger("agentlint.test.idempotent")
    handler_count = len(logger.handlers)

    configured_logger = configure_json_logger("agentlint.test.idempotent")

    assert configured_logger is logger
    assert len(logger.handlers) == handler_count
