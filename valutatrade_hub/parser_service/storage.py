from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from valutatrade_hub.infra.settings import SettingsLoader


class RatesStorage:
    """Работа с историей и кешем курсов."""

    def __init__(self) -> None:
        settings = SettingsLoader()
        self._history_path = settings.get("EXCHANGE_RATES_HISTORY_PATH")
        self._cache_path = settings.get("RATES_PATH")

    def _atomic_write(self, path: str, data: Any) -> None:
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)

    def _read_json(self, path: str, default: Any) -> Any:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default

    def append_history(self, records: list[dict]) -> None:
        history: list[dict] = self._read_json(self._history_path, [])

        existing_ids = {item["id"] for item in history if "id" in item}
        new_records = [r for r in records if r["id"] not in existing_ids]

        if not new_records:
            return

        history.extend(new_records)
        self._atomic_write(self._history_path, history)

    def read_cache(self) -> dict:
        return self._read_json(
            self._cache_path,
            {"pairs": {}, "last_refresh": None},
        )

    def write_cache(self, pairs_update: dict[str, dict], refresh_ts: str) -> None:
        cache = self.read_cache()
        pairs = cache.get("pairs", {})

        for pair, data in pairs_update.items():
            current = pairs.get(pair)
            if current is None or data["updated_at"] > current["updated_at"]:
                pairs[pair] = data

        cache["pairs"] = pairs
        cache["last_refresh"] = refresh_ts

        self._atomic_write(self._cache_path, cache)

def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
