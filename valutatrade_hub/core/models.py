from __future__ import annotations

from datetime import datetime
from typing import Dict

from .utils import (
    validate_username,
    validate_password,
    hash_password,
    make_salt,
    parse_iso,
)
from .exceptions import InsufficientFundsError

class User:
    """Пользователь системы."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: str,
    ) -> None:
        self._user_id = user_id
        self._username = validate_username(username)
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        self._username = validate_username(value)

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def hashed_password(self) -> str:
        return self._hashed_password


    @property
    def registration_date(self) -> datetime:
        return parse_iso(self._registration_date)

    def get_user_info(self) -> Dict[str, str]:
        """Информация без пароля."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date,
        }

    def verify_password(self, password: str) -> bool:
        """Проверка пароля."""
        candidate = hash_password(password, self._salt)
        return candidate == self._hashed_password

    def change_password(self, new_password: str) -> None:
        """Смена пароля."""
        validate_password(new_password)
        new_salt = make_salt()
        new_hash = hash_password(new_password, new_salt)

        self._salt = new_salt
        self._hashed_password = new_hash

class Wallet:
    """Кошелёк валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        self.currency_code = currency_code
        self._balance = 0.0
        self.balance = balance

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Баланс должен быть числом")
        value_f = float(value)
        if value_f < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = value_f

    def deposit(self, amount: float) -> None:
        amount_f = float(amount)
        if amount_f <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        self.balance = self.balance + amount_f

    def withdraw(self, amount: float) -> None:
        amount_f = float(amount)
        if amount_f <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        if amount_f > self.balance:
            raise InsufficientFundsError(self.balance, amount_f, self.currency_code)
        self.balance = self.balance - amount_f

    def get_balance_info(self) -> str:
        return f"{self.currency_code}: {self.balance:.4f}"

class Portfolio:
    """Портфель пользователя."""

    def __init__(
        self,
        user_id: int,
        wallets: dict[str, Wallet] | None = None,
        user: User | None = None,
    ) -> None:
        self._user_id = user_id
        self._wallets: dict[str, Wallet] = wallets or {}
        self._user = user

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def user(self) -> User:
        if self._user is None:
            raise ValueError("User не загружен")
        return self._user


    @property
    def wallets(self) -> dict[str, Wallet]:
        return dict(self._wallets)

    def add_currency(self, currency_code: str) -> None:
        code = currency_code.strip().upper()
        if code in self._wallets:
            raise ValueError("Кошелёк уже существует")
        self._wallets[code] = Wallet(code, 0.0)

    def get_wallet(self, currency_code: str) -> Wallet:
        code = currency_code.strip().upper()
        if code not in self._wallets:
            raise ValueError(f"Кошелёк '{code}' не найден")
        return self._wallets[code]

    def get_total_value(self, base_currency: str = "USD") -> float:
        base = base_currency.strip().upper()
        exchange_rates = {
            "EUR_USD": 1.08,
            "BTC_USD": 60000.0,
            "ETH_USD": 3000.0,
            "RUB_USD": 0.011,
        }

        total = 0.0
        for code, wallet in self._wallets.items():
            if code == base:
                total += wallet.balance
                continue

            pair = f"{code}_{base}"
            if pair not in exchange_rates:
                raise ValueError(f"Нет курса для {code}->{base}")
            total += wallet.balance * exchange_rates[pair]

        return total

