"""Structured logging with structlog.

Provides:
- JSON-formatted log output for production
- Context processors for request_id, user_id, workspace_id
- Factory function for creating loggers
"""

import logging
import sys
from typing import Optional
from uuid import UUID

import structlog
from structlog.types import EventDict, WrappedLogger


# Global context for request-scoped data
_context_vars: dict[str, str] = {}


def add_request_context(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Add request context (request_id, user_id, workspace_id) to log entries."""
    if _context_vars:
        event_dict.update(_context_vars)
    return event_dict


def add_service_info(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Add service information to log entries."""
    event_dict["service"] = "workflow-orchestrator"
    return event_dict


def configure_structlog(
    json_format: bool = True,
    log_level: str = "INFO",
) -> None:
    """Configure structlog for the application.

    Args:
        json_format: If True, output JSON logs (for production).
                     If False, output human-readable logs (for development).
        log_level: The minimum log level to output (DEBUG, INFO, WARNING, ERROR).
    """
    # Set up stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Define shared processors
    shared_processors: list = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_service_info,
        add_request_context,
    ]

    if json_format:
        # JSON format for production
        structlog.configure(
            processors=shared_processors + [
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Human-readable format for development
        structlog.configure(
            processors=shared_processors + [
                structlog.processors.format_exc_info,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger with the given name.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        A structlog BoundLogger instance.

    Example:
        logger = get_logger(__name__)
        logger.info("user_logged_in", user_id=str(user.id), email=user.email)
    """
    return structlog.get_logger(name)


def bind_context(
    request_id: Optional[str] = None,
    user_id: Optional[UUID] = None,
    workspace_id: Optional[UUID] = None,
) -> None:
    """Bind context variables for the current request scope.

    These values will be included in all subsequent log entries
    until clear_context() is called.

    Args:
        request_id: Unique identifier for the current request.
        user_id: ID of the authenticated user.
        workspace_id: ID of the current workspace context.
    """
    if request_id:
        _context_vars["request_id"] = request_id
    if user_id:
        _context_vars["user_id"] = str(user_id)
    if workspace_id:
        _context_vars["workspace_id"] = str(workspace_id)


def clear_context() -> None:
    """Clear all bound context variables.

    Should be called at the end of request processing.
    """
    _context_vars.clear()


def with_context(**kwargs) -> dict[str, str]:
    """Create a context dict for temporary binding.

    Returns the context dict that was added, which can be used
    to selectively unbind later.

    Example:
        ctx = with_context(operation="batch_process", batch_id="123")
        # ... do work ...
        for key in ctx:
            _context_vars.pop(key, None)
    """
    for key, value in kwargs.items():
        if value is not None:
            _context_vars[key] = str(value) if not isinstance(value, str) else value
    return {k: v for k, v in kwargs.items() if v is not None}


# Initialize with sensible defaults
# Can be reconfigured by calling configure_structlog() in main.py
configure_structlog(json_format=False, log_level="INFO")
