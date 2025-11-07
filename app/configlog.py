import json
import logging
import os
import sys
from typing import Any

import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler

IS_GCP: bool = any(
    [
        os.getenv("K_SERVICE"),  # Cloud Run
        os.getenv("FUNCTION_TARGET"),  # Cloud Functions
        os.getenv("GAE_SERVICE"),  # App Engine
    ]
)

LOG_LEVEL: str = os.getenv("LOG_SEVERITY_LEVEL", "DEBUG").upper()

# ANSI escape sequences for colors
COLORS: dict[str, str] = {
    "DEBUG": "\033[94m",  # Blue
    "INFO": "\033[92m",  # Green
    "WARNING": "\033[93m",  # Yellow
    "ERROR": "\033[91m",  # Red
    "CRITICAL": "\033[95m",  # Magenta
    "RESET": "\033[0m",
    "DIM": "\033[2m",
    "CYAN": "\033[96m",
    "BOLD_YELLOW": "\033[1;33m",
    "BOLD_RED": "\033[1;31m",
}


# Custom formatter with color support
class ColoredFormatter(logging.Formatter):
    def format(
        self,
        record: logging.LogRecord,
    ) -> str:
        if IS_GCP:
            # In produzione: log strutturato (JSON)
            log_entry: dict[str, Any] = {
                "severity": record.levelname,
                "logger": record.name,
                "funcName": record.funcName,
                "lineno": record.lineno,
                "message": record.getMessage(),
                "time": self.formatTime(record, self.datefmt),
            }
            return json.dumps(log_entry)

        reset: str = COLORS["RESET"]
        level_color: str = COLORS.get(record.levelname, "")
        name_color: str = COLORS["CYAN"]
        func_color: str = COLORS["BOLD_YELLOW"]
        line_color: str = COLORS["BOLD_RED"]

        # Color parts of the log record
        record.levelname = f"{level_color}{record.levelname:<8}{reset}"
        record.asctime = f"\033[1m{self.formatTime(record, self.datefmt)}{reset}"
        record.name = f"{name_color}{record.name}{reset}"
        record.funcName = f"{func_color}{record.funcName}{reset}"
        record.lineno = f"{line_color}{record.lineno}{reset}"  # pyright: ignore[reportAttributeAccessIssue]

        return super().format(record)


# Get severity level from environment
logger: logging.Logger = logging.getLogger("partyup-be")
logger.setLevel(LOG_LEVEL)
logger.handlers.clear()

if IS_GCP:
    # → Produzione: usa Cloud Logging
    import google.cloud.logging
    from google.cloud.logging.handlers import CloudLoggingHandler

    client = google.cloud.logging.Client()
    handler = CloudLoggingHandler(client)
    handler.setLevel(LOG_LEVEL)
    logger.addHandler(handler)
else:
    # Create handler for stderr
    handler: logging.Handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(LOG_LEVEL)
    # Define log format
    formatter = ColoredFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s:%(funcName)s:%(lineno)s - %(message)s\n",
        datefmt="%Y-%m-%d %H:%M:%S.%f",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
