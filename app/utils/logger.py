"""Application-wide logging setup."""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging() -> logging.Logger:
    """Configure the 'lojaflow' logger with file and console handlers."""
    log_dir = Path.home() / ".lojaflow" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "lojaflow.log"

    logger = logging.getLogger("lojaflow")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger  # Already configured

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — rotates at 5MB, keeps 3 backups
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler (stderr) — only warnings and above
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str = "lojaflow") -> logging.Logger:
    """Get a child logger under the 'lojaflow' namespace."""
    return logging.getLogger(f"lojaflow.{name}" if name != "lojaflow" else name)
