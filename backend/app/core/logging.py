# backend/app/core/logging.py

import logging
import sys
from pathlib import Path
from typing import Optional


class ColorFormatter(logging.Formatter):
    """Pretty, color-coded console output."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[41m",
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = self.formatTime(record, "%H:%M:%S")
        level = f"{color}{self.BOLD}{record.levelname:<8}{self.RESET}"
        name = f"\033[90m{record.name}\033[0m"
        message = record.getMessage()
        line = f"{timestamp} | {level} | {name} | {message}"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


class PlainFileFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        return f"{timestamp} | {record.levelname:<8} | {record.name} | {record.getMessage()}"


def setup_logging(level: str = "INFO") -> None:
    """Call ONCE at the top of any entrypoint. Sets up both 'app' and 'audit' loggers."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # -- app logger (operational, pretty console + file) --
    app_logger = logging.getLogger("app")
    app_logger.setLevel(level.upper())
    app_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColorFormatter())
    app_logger.addHandler(console_handler)

    app_file_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    app_file_handler.setFormatter(PlainFileFormatter())
    app_logger.addHandler(app_file_handler)

    app_logger.propagate = False

    # -- audit logger (compliance trail, file only, always INFO) --
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO)
    audit_logger.handlers.clear()

    audit_file_handler = logging.FileHandler(log_dir / "audit.log", encoding="utf-8")
    audit_file_handler.setFormatter(PlainFileFormatter())
    audit_logger.addHandler(audit_file_handler)

    audit_logger.propagate = False

    app_logger.info("=" * 60)
    app_logger.info("Logging initialized")
    app_logger.info("=" * 60)


def get_logger(name: str) -> logging.Logger:
    """Standard app logger — use this in most files."""
    return logging.getLogger(f"app.{name}")


def get_app_logger() -> logging.Logger:
    """Back-compat alias — same as get_logger('') essentially, returns the root app logger."""
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
    """Single entry point for writing a compliance audit line."""
    get_audit_logger().info(
        f"intent='{user_intent[:100]}' | triggered_rails={triggered_rails} | "
        f"has_pii={has_pii} | escalation_type={escalation_type}"
    )