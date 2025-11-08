import json
import logging
import os
import sys
import traceback
from collections.abc import Callable
from functools import wraps
from typing import Any, TextIO

from fastapi import HTTPException
from starlette import status

IS_GCP: bool = any(
    [
        os.getenv("K_SERVICE"),  # Cloud Run
        os.getenv("FUNCTION_TARGET"),  # Cloud Functions
        os.getenv("GAE_SERVICE"),  # App Engine
    ]
)

LOG_LEVEL: str = os.getenv("LOG_SEVERITY_LEVEL", "DEBUG").upper()

COLORS: dict[str, str] = {
    "DEBUG": "\033[94m",
    "INFO": "\033[92m",
    "WARNING": "\033[93m",
    "ERROR": "\033[91m",
    "CRITICAL": "\033[95m",
    "RESET": "\033[0m",
    "CYAN": "\033[96m",
    "BOLD_YELLOW": "\033[1;33m",
    "BOLD_RED": "\033[1;31m",
}


class ColoredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if IS_GCP:
            log_entry: dict[str, Any] = {
                "severity": record.levelname,
                "logger": record.name,
                "funcName": record.funcName,
                "lineno": record.lineno,
                "message": record.getMessage(),
                "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            }
            return json.dumps(log_entry)

        reset: str = COLORS["RESET"]
        level_color: str = COLORS.get(record.levelname, "")
        asctime: str = f"\033[1m{self.formatTime(record, self.datefmt)}{reset}"
        level: str = f"{level_color}{record.levelname:<8}{reset}"
        name: str = f"{COLORS['CYAN']}{record.name}{reset}"
        func: str = f"{COLORS['BOLD_YELLOW']}{record.funcName}{reset}"
        lineno: str = f"{COLORS['BOLD_RED']}{record.lineno}{reset}"
        message: str = record.getMessage()

        return f"{asctime} {level} {name}:{func}:{lineno} - {message}\n"


def set_logger() -> logging.Logger:
    logger: logging.Logger = logging.getLogger("partyup-be")
    logger.setLevel(LOG_LEVEL)
    logger.handlers.clear()
    logger.propagate = False

    if IS_GCP:
        from google.cloud import logging as gcp_logging
        from google.cloud.logging.handlers import CloudLoggingHandler

        client = gcp_logging.Client()
        handler = CloudLoggingHandler(client)
        handler.setLevel(LOG_LEVEL)
        logger.addHandler(handler)
    else:
        handler: logging.StreamHandler[TextIO | Any] = logging.StreamHandler(sys.stderr)
        handler.setLevel(LOG_LEVEL)
        formatter = ColoredFormatter(datefmt="%Y-%m-%d %H:%M:%S.%f")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger: logging.Logger = set_logger()


def log(
    func: Callable[..., Any],
    logger: logging.Logger = set_logger(),
) -> Any:
    @wraps(wrapped=func)
    async def wrapper(
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        try:
            logger.info(f"Calling: {func.__name__}")
            rv: Any = await func(*args, **kwargs)
            logger.info(f"Success: {func.__name__}")
            return rv
        except HTTPException as e:
            logger.error(
                f"ERROR: handled exception raised at: {func.__name__}",
                e,
                traceback.print_exc(),
            )
            raise e
        except Exception as e:
            logger.critical(
                f"CRITICAL: unexpected error raised: {func.__name__}",
                e,
                traceback.print_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=e,
            ) from e

    return wrapper
