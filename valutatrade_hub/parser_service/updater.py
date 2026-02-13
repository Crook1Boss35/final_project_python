from __future__ import annotations

from typing import Iterable

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.storage import RatesStorage, utc_now_iso


class RatesUpdater:
    """Оркестратор обновления курсов и сохранения истории."""

    def __init__(
        self,
        clients: Iterable,
        storage: RatesStorage,
    ) -> None:
        self.clients = list(clients)
        self.storage = storage

    def run_update(self, source: str | None = None) -> dict:
        collected: dict[str, dict] = {}
        history_records: list[dict] = []

        errors: list[str] = []

        for client in self.clients:
            name = client.__class__.__name__.lower()

            if source and source not in name:
                continue

            try:
                data = client.fetch_rates()
            except ApiRequestError as e:
                errors.append(str(e))
                continue

            for pair, payload in data.items():
                collected[pair] = {
                    "rate": payload["rate"],
                    "updated_at": payload["updated_at"],
                    "source": payload["source"],
                }

                history_records.append(
                    {
                        "id": f"{pair}_{payload['updated_at']}",
                        "from_currency": pair.split("_")[0],
                        "to_currency": pair.split("_")[1],
                        "rate": payload["rate"],
                        "timestamp": payload["updated_at"],
                        "source": payload["source"],
                        "meta": payload.get("meta", {}),
                    }
                )

        if collected:
            refresh_ts = utc_now_iso()
            self.storage.write_cache(collected, refresh_ts)
            self.storage.append_history(history_records)
        else:
            refresh_ts = None

        return {
            "updated_count": len(collected),
            "last_refresh": refresh_ts,
            "errors": errors,
        }
