"""Reusable logging utilities for the Google Maps Business Extractor."""

from __future__ import annotations

import logging
from datetime import datetime
from logging import Logger
from pathlib import Path

from app.config import AppConfig


def _build_log_file_path(log_dir: Path) -> Path:
    """Create the daily log file path."""

    current_date = datetime.now().strftime("%Y-%m-%d")
    return log_dir / f"google_maps_extractor_{current_date}.log"


def get_logger(name: str = "google_maps_extractor", config: AppConfig | None = None) -> Logger:
    """Return a configured logger instance with console and file handlers."""

    resolved_config = config or AppConfig.from_env()
    resolved_config.log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if getattr(logger, "_gme_configured", False):
        return logger

    logger.setLevel(getattr(logging, resolved_config.log_level.upper(), logging.INFO))
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logger.level)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(
        _build_log_file_path(resolved_config.log_dir),
        encoding="utf-8",
    )
    file_handler.setLevel(logger.level)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger._gme_configured = True  # type: ignore[attr-defined]

    return logger
