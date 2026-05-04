"""
Logging configuration module.
Setup structured logging with JSON support.
"""
import logging
import sys
from pythonjsonlogger import jsonlogger

from app.core.config import settings


def setup_logging():
    """Configure application logging."""
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)

    # Remove default handlers
    root_logger.handlers = []

    # Console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    json_formatter = jsonlogger.JsonFormatter(
        "%(timestamp)s %(level)s %(name)s %(message)s"
    )
    console_handler.setFormatter(json_formatter)
    root_logger.addHandler(console_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("librosa").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return root_logger


# Get application logger
logger = logging.getLogger("bird_search_api")
