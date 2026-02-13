from __future__ import annotations

from typing import Any


class SettingsLoader:
    """Конфиг проекта."""

    _instance: "SettingsLoader | None" = None

    def __new__(cls) -> "SettingsLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = {
                "USERS_PATH": "data/users.json",
                "PORTFOLIOS_PATH": "data/portfolios.json",
                "RATES_PATH": "data/rates.json",
                "EXCHANGE_RATES_HISTORY_PATH": "data/exchange_rates.json",
                "RATES_TTL_SECONDS": 300,
                "DEFAULT_BASE_CURRENCY": "USD",
                "LOG_PATH": "logs/actions.log",
                "LOG_LEVEL": "INFO",
                "LOG_ROTATE_BYTES": 200_000,
                "LOG_ROTATE_BACKUP_COUNT": 3,
            }
        return cls._instance

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def reload(self) -> None:
        return

