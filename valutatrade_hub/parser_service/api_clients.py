from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import utc_now_iso


class BaseApiClient(ABC):
    """Базовый клиент API."""

    def __init__(self, config: ParserConfig) -> None:
        self.config = config

    @abstractmethod
    def fetch_rates(self) -> dict[str, dict[str, Any]]:
        pass


class CoinGeckoClient(BaseApiClient):
    """Клиент CoinGecko."""

    def fetch_rates(self) -> dict[str, dict[str, Any]]:
        ids = [
            self.config.CRYPTO_ID_MAP[c]
            for c in self.config.CRYPTO_CURRENCIES
        ]

        params = {
            "ids": ",".join(ids),
            "vs_currencies": self.config.BASE_CURRENCY.lower(),
        }

        start = time.perf_counter()
        try:
            response = requests.get(
                self.config.COINGECKO_URL,
                params=params,
                timeout=self.config.REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"CoinGecko network error: {e}") from e

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if response.status_code != 200:
            raise ApiRequestError(
                f"CoinGecko API error: {response.status_code}"
            )

        data = response.json()
        timestamp = utc_now_iso()

        result: dict[str, dict[str, Any]] = {}

        for code in self.config.CRYPTO_CURRENCIES:
            raw_id = self.config.CRYPTO_ID_MAP[code]
            if raw_id not in data:
                continue

            price = data[raw_id].get(self.config.BASE_CURRENCY.lower())
            if not isinstance(price, (int, float)):
                continue

            pair = f"{code}_{self.config.BASE_CURRENCY}"
            result[pair] = {
                "rate": float(price),
                "updated_at": timestamp,
                "source": "CoinGecko",
                "meta": {
                    "raw_id": raw_id,
                    "request_ms": elapsed_ms,
                    "status_code": response.status_code,
                    "etag": response.headers.get("ETag"),
                },
            }

        return result


class ExchangeRateApiClient(BaseApiClient):
    """Клиент ExchangeRate-API."""

    def fetch_rates(self) -> dict[str, dict[str, Any]]:
        if not self.config.EXCHANGERATE_API_KEY:
            raise ApiRequestError("ExchangeRate API key is missing")

        url = (
            f"{self.config.EXCHANGERATE_API_URL}/"
            f"{self.config.EXCHANGERATE_API_KEY}/"
            f"latest/{self.config.BASE_CURRENCY}"
        )

        start = time.perf_counter()
        try:
            response = requests.get(
                url,
                timeout=self.config.REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"ExchangeRate network error: {e}") from e

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if response.status_code != 200:
            err: dict[str, Any] = {}
            try:
                parsed = response.json()
                if isinstance(parsed, dict):
                    err = parsed
            except ValueError:
                err = {"error": response.text[:200]}

            detail = (
                err.get("error-type")
                or err.get("error")
                or err.get("message")
                or "unknown error"
            )
            raise ApiRequestError(f"ExchangeRate API error {response.status_code}: {detail}")

        payload = response.json()

        if payload.get("result") != "success":
            raise ApiRequestError("ExchangeRate API returned failure")

        rates = payload.get("conversion_rates") or payload.get("rates") or {}
        timestamp = utc_now_iso()

        result: dict[str, dict[str, Any]] = {}

        for code in self.config.FIAT_CURRENCIES:
            raw = rates.get(code)
            if not isinstance(raw, (int, float)):
                continue

            raw_f = float(raw)
            if raw_f == 0:
                continue

            pair = f"{code}_{self.config.BASE_CURRENCY}"
            result[pair] = {
                "rate": 1 / raw_f,
                "updated_at": timestamp,
                "source": "ExchangeRate-API",
                "meta": {
                    "request_ms": elapsed_ms,
                    "status_code": response.status_code,
                    "base_code": payload.get("base_code", self.config.BASE_CURRENCY),
                },
            }
        return result
