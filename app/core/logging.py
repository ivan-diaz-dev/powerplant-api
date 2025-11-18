# -*- coding: utf-8 -*-

import logging

_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(level: str | int = "INFO") -> None:
    """Configure the root logger with a sensible default format."""

    resolved_level = _translate_level(level)
    logging.basicConfig(level=resolved_level, format=_LOG_FORMAT)


def _translate_level(level: str | int) -> int:
    if isinstance(level, int):
        return level

    normalized = level.upper()
    return getattr(logging, normalized, logging.INFO)
