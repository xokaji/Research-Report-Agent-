"""
utils/logger.py — Structured logging for the whole pipeline.
Writes to both stdout (coloured) and logs/research.log (plain JSON-like).
"""

import logging
import sys
import os
from datetime import datetime

os.makedirs("logs", exist_ok=True)

# ── Formatters ────────────────────────────────────────────────────────────────
_CONSOLE_FMT = "%(asctime)s  %(levelname)-8s  %(name)s  │  %(message)s"
_FILE_FMT    = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_DATE_FMT    = "%H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger that:
      • Prints INFO+ to stdout with readable formatting
      • Writes DEBUG+ to logs/research.log
    """
    logger = logging.getLogger(name)
    if logger.handlers:          # avoid duplicate handlers on reimport
        return logger

    logger.setLevel(logging.DEBUG)

    # Console handler — INFO and above
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(_CONSOLE_FMT, datefmt=_DATE_FMT))

    # File handler — everything (DEBUG included)
    log_file = f"logs/research_{datetime.now().strftime('%Y%m%d')}.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(_FILE_FMT))

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger
