"""Structured logging helpers used by AgentLint components and experiment runners."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Final

_STANDARD_LOG_RECORD_FIELDS: Final[frozenset[str]] = frozenset(
    logging.makeLogRecord({}).__dict__.keys()
)


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects with preserved extra fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Return a structured representation of ``record`` suitable for machine parsing."""
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(
            {
                field: value
                for field, value in record.__dict__.items()
                if field not in _STANDARD_LOG_RECORD_FIELDS and not field.startswith("_")
            }
        )
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, sort_keys=True)


def configure_json_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return an idempotently configured logger that emits JSON records to stderr.

    Args:
        name: Logger name, normally the module ``__name__``.
        level: Standard-library logging level for the logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    has_json_handler = any(
        isinstance(handler.formatter, JsonFormatter) for handler in logger.handlers
    )
    if not has_json_handler:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    return logger
