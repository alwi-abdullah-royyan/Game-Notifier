import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_file: Path, max_bytes: int, backup_count: int) -> logging.Logger:
    logger = logging.getLogger("game_notifier")
    logger.setLevel(logging.INFO)

    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))

    logger.addHandler(handler)
    logger.propagate = False
    return logger
