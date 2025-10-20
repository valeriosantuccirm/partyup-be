# import os
# import sys

# from logtail import LogtailHandler
# from loguru import logger

# DEFAULT_LEVEL: str = "DEBUG"
# token: str | None = os.environ.get("LOGTAIL_SOURCE_TOKEN")

# # specify severity level
# severity_level: str = os.environ.get("LOG_SEVERITY_LEVEL", default=DEFAULT_LEVEL)

# # config logger for stderr
# logger.remove()
# logger.add(
#     sink=sys.stderr,
#     backtrace=True,
#     diagnose=True,
#     level=DEFAULT_LEVEL,
# )

# # config logger for Logtail
# loghandler = LogtailHandler(source_token=token)
# logger.add(
#     sink=loghandler,
#     format="{time:MMMM D, YYYY - HH:mm:ss} {level} - {message}",
#     backtrace=True,
#     diagnose=True,
#     level=severity_level,
# )


import logging
import os
import sys

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
    def format(self, record: logging.LogRecord) -> str:
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
SECURITY_LEVEL: str = os.getenv("LOG_SEVERITY_LEVEL", "DEBUG").upper()

# Configure root logger
logger: logging.Logger = logging.getLogger()
logger.setLevel(SECURITY_LEVEL)

# Create handler for stderr
handler: logging.Handler = logging.StreamHandler(sys.stderr)
handler.setLevel(SECURITY_LEVEL)

# Define log format
formatter = ColoredFormatter(
    fmt="%(asctime)s %(levelname)s %(name)s:%(funcName)s:%(lineno)s - %(message)s\n",
    datefmt="%Y-%m-%d %H:%M:%S.%f",
)

handler.setFormatter(formatter)
logger.handlers.clear()  # Remove any existing handlers
logger.addHandler(handler)
