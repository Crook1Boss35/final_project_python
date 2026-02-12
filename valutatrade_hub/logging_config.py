from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader


def setup_logging() -> None:
    settings = SettingsLoader()
    log_path = str(settings.get("LOG_PATH", "logs/actions.log"))
    level_name = str(settings.get("LOG_LEVEL", "INFO")).upper()
    max_bytes = int(settings.get("LOG_ROTATE_BYTES", 200_000))
    backups = int(settings.get("LOG_ROTATE_BACKUP_COUNT", 3))

    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)

    logger = logging.getLogger("valutatrade")
    logger.setLevel(getattr(logging, level_name, logging.INFO))
    logger.propagate = False

    if logger.handlers:
        return

    fmt = logging.Formatter("%(levelname)s %(asctime)s %(message)s")

    handler = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backups, encoding="utf-8")
    handler.setFormatter(fmt)
    logger.addHandler(handler)

