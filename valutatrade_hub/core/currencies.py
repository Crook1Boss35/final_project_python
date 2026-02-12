from __future__ import annotations

from abc import ABC, abstractmethod

from .exceptions import CurrencyNotFoundError


def _validate_code(code: str) -> str:
    if not isinstance(code, str):
        raise CurrencyNotFoundError(str(code))
    value = code.strip().upper()
    if value == "" or " " in value or not (2 <= len(value) <= 5):
        raise CurrencyNotFoundError(value if value else str(code))
    return value


def _validate_name(name: str) -> str:
    if not isinstance(name, str):
        raise ValueError("name должен быть строкой")
    value = name.strip()
    if value == "":
        raise ValueError("name не может быть пустым")
    return value


class Currency(ABC):
    """Валюта."""

    def __init__(self, name: str, code: str) -> None:
        self.name = _validate_name(name)
        self.code = _validate_code(code)

    @abstractmethod
    def get_display_info(self) -> str:
        """Строка для UI."""
        raise NotImplementedError


class FiatCurrency(Currency):
    """Фиат."""

    def __init__(self, name: str, code: str, issuing_country: str) -> None:
        super().__init__(name, code)
        self.issuing_country = _validate_name(issuing_country)

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Крипто."""

    def __init__(self, name: str, code: str, algorithm: str, market_cap: float) -> None:
        super().__init__(name, code)
        self.algorithm = _validate_name(algorithm)
        self.market_cap = float(market_cap)

    def get_display_info(self) -> str:
        return f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"


_REGISTRY: dict[str, Currency] = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", 4.50e11),
}


def get_currency(code: str) -> Currency:
    key = _validate_code(code)
    if key not in _REGISTRY:
        raise CurrencyNotFoundError(key)
    return _REGISTRY[key]


def list_supported_codes() -> list[str]:
    return sorted(_REGISTRY.keys())
