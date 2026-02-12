from __future__ import annotations

from typing import Any

from valutatrade_hub.core.utils import load_json, save_json
from .settings import SettingsLoader


class DatabaseManager:
    """Доступ к JSON."""

    _instance: "DatabaseManager | None" = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = SettingsLoader()
        return cls._instance

    def _path(self, key: str) -> str:
        value = self._settings.get(key)
        if not isinstance(value, str) or value.strip() == "":
            raise ValueError(f"Некорректный путь: {key}")
        return value

    def read_users(self) -> list[dict[str, Any]]:
        return load_json(self._path("USERS_PATH"), [])

    def write_users(self, users: list[dict[str, Any]]) -> None:
        save_json(self._path("USERS_PATH"), users)

    def read_portfolios(self) -> list[dict[str, Any]]:
        return load_json(self._path("PORTFOLIOS_PATH"), [])

    def write_portfolios(self, portfolios: list[dict[str, Any]]) -> None:
        save_json(self._path("PORTFOLIOS_PATH"), portfolios)

    def read_rates(self) -> dict[str, Any]:
        return load_json(self._path("RATES_PATH"), {})

    def write_rates(self, rates: dict[str, Any]) -> None:
        save_json(self._path("RATES_PATH"), rates)
