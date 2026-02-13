from __future__ import annotations

import time

from valutatrade_hub.parser_service.updater import RatesUpdater


def run_periodic(updater: RatesUpdater, interval_seconds: int) -> None:
    """Периодический запуск обновления."""
    while True:
        updater.run_update()
        time.sleep(interval_seconds)
