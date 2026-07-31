# backend/app/core/logging.py

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import get_settings

# ---------------------------------------------------------------------------
# Context vars — set once per incoming request/chat turn, read by every
# log call underneath it without having to thread session_id through every
# function signature manually.
# ---------------------------------------------------------------------------
session_id_var: ContextVar[Optional[str]] = ContextVar("session_id", default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class JSONFormatter(logging.Formatter):
    """
    Renders each log record as one JSON line. Structured logs are what let you
    grep/query "show me every audit line where has_pii=true" instead of
    regexing free-text log messages.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "session_id": session_id_var.get(),
            "request_id": request_id_var.get(),
        }

        # Anything passed via extra={...} in a log call gets merged in flat,
        # e.g. logger.info("...", extra={"triggered_rails": [...]})
        reserved = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "message",
        }
        for key, value in record.__dict__.items():
            if key not in reserved and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def _make_file_handler(path: Path) -> logging.Handler:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(JSONFormatter())
    return handler


def setup_logging() -> None:
    """
    Call once at app startup (main.py). Configures two independent loggers:

    - "app"   -> logs/app.log   : requests, latency, errors, rail exceptions
    - "audit" -> logs/audit.log : compliance trail — one line per chat turn,
                                  matching the log_hr_audit() action shape
                                  (session_id, intent, triggered_rails, has_pii,
                                  escalation_type)

    Kept as two separate loggers/files (not one combined stream) because they
    have different audiences and retention needs: app.log is for on-call
    debugging and can be rotated/discarded quickly; audit.log is the
    compliance record HR/legal may need to retain and review, so it should
    never be mixed with noisy operational logs or accidentally dropped by a
    debug-log filter.
    """
    settings = get_settings()
    log_dir = Path("logs")

    # -- app logger --
    app_logger = logging.getLogger("app")
    app_logger.setLevel(settings.log_level.upper())
    app_logger.handlers.clear()
    app_logger.addHandler(_make_file_handler(log_dir / "app.log"))

    # also echo to stdout in development so you see it in the terminal
    if settings.environment == "development":
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(JSONFormatter())
        app_logger.addHandler(stream_handler)

    app_logger.propagate = False

    # -- audit logger --
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO)  # audit lines are never debug-filtered out
    audit_logger.handlers.clear()
    audit_logger.addHandler(_make_file_handler(log_dir / "audit.log"))
    audit_logger.propagate = False


def get_app_logger() -> logging.Logger:
    return logging.getLogger("app")


def get_audit_logger() -> logging.Logger:
    return logging.getLogger("audit")


def log_audit_event(
    *,
    user_intent: str,
    triggered_rails: list[str],
    has_pii: bool = False,
    escalation_type: Optional[str] = None,
) -> None:
    """
    Single entry point for writing an audit line — mirrors the log_hr_audit()
    action from the guardrails proposal, so it can be called directly from
    actions.py without duplicating the field list everywhere.
    """
    get_audit_logger().info(
        "hr_policy_desk_audit",
        extra={
            "user_intent": user_intent,
            "triggered_rails": triggered_rails,
            "has_pii": has_pii,
            "escalation_type": escalation_type,
        },
    )