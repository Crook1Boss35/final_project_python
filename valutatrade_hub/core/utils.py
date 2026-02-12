from __future__ import annotations

import json
import os
import secrets
import hashlib
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    """Текущая дата в ISO UTC."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso(dt_str: str) -> datetime:
    """Парсинг ISO-строки."""
    return datetime.fromisoformat(dt_str)


def validate_username(username: str) -> str:
    """Проверка имени."""
    if not isinstance(username, str):
        raise ValueError("Username должен быть строкой")
    value = username.strip()
    if value == "":
        raise ValueError("Имя пользователя не может быть пустым")
    return value


def validate_password(password: str) -> str:
    """Проверка пароля."""
    if not isinstance(password, str):
        raise ValueError("Пароль должен быть строкой")
    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")
    return password

def normalize_currency_code(code: str) -> str:
    """Код валюты."""
    if not isinstance(code, str):
        raise ValueError("currency_code должен быть строкой")
    value = code.strip().upper()
    if value == "":
        raise ValueError("currency_code не может быть пустым")
    if " " in value or not (2 <= len(value) <= 5):
        raise ValueError(f"Некорректный код валюты '{value}'")
    return value

def validate_amount(amount: Any) -> float:
    """Проверка суммы > 0."""
    if isinstance(amount, bool):
        raise ValueError("'amount' должен быть положительным числом")

    if isinstance(amount, (int, float)):
        value = float(amount)
    elif isinstance(amount, str):
        try:
            value = float(amount)
        except ValueError as exc:
            raise ValueError("'amount' должен быть положительным числом") from exc
    else:
        raise ValueError("'amount' должен быть положительным числом")

    if value <= 0:
        raise ValueError("'amount' должен быть положительным числом")

    return value


def make_salt(nbytes: int = 8) -> str:
    """Генерация соли."""
    return secrets.token_urlsafe(nbytes)


def hash_password(password: str, salt: str) -> str:
    """SHA256(password+salt)."""
    data = (password + salt).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def load_json(path: str, default: Any) -> Any:
    """Загрузка JSON."""
    if not os.path.exists(path):
        return default

    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()
        if raw == "":
            return default
        return json.loads(raw)


def save_json(path: str, data: Any) -> None:
    """Сохранение JSON."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    os.replace(tmp, path)
