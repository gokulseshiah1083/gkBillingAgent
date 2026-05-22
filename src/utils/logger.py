"""Logging utilities."""

from __future__ import annotations

from typing import Any, Dict
import logging


def setup_logging(logging_config: Dict[str, Any]) -> None:
    level_str = (logging_config.get("level") or "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
