import os
import sys

from logtail import LogtailHandler
from loguru import logger

DEFAULT_LEVEL: str = "DEBUG"
token: str | None = os.environ.get("LOGTAIL_SOURCE_TOKEN")

# specify severity level
severity_level: str = os.environ.get("LOG_SEVERITY_LEVEL", default=DEFAULT_LEVEL)

# config logger for stderr
logger.remove()
logger.add(
    sink=sys.stderr,
    backtrace=True,
    diagnose=True,
    level=DEFAULT_LEVEL,
)

# config logger for Logtail
loghandler = LogtailHandler(source_token=token)
logger.add(
    sink=loghandler,
    format="{time:MMMM D, YYYY - HH:mm:ss} {level} - {message}",
    backtrace=True,
    diagnose=True,
    level=severity_level,
)
