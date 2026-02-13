from __future__ import annotations

from typing import Any

from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader

from .currencies import get_currency
from .exceptions import ApiRequestError
from .models import User, Wallet, Portfolio
from .utils import (
    validate_username,
    validate_password,
    make_salt,
    hash_password,
    now_iso,
    parse_iso,
    validate_amount,
    normalize_currency_code,
)


EXCHANGE_RATES = {
    "EUR_USD": 1.08,
    "BTC_USD": 60000.0,
    "ETH_USD": 3000.0,
    "RUB_USD": 0.011,
}


def _db() -> DatabaseManager:
    return DatabaseManager()


def _settings() -> SettingsLoader:
    return SettingsLoader()


def _next_user_id(users: list[dict[str, Any]]) -> int:
    if not users:
        return 1
    return max(int(u["user_id"]) for u in users) + 1


def _pair_key(from_code: str, to_code: str) -> str:
    return f"{from_code}_{to_code}"


def _ensure_wallet(portfolio: Portfolio, currency: str) -> Wallet:
    if currency not in portfolio.wallets:
        portfolio.add_currency(currency)
    return portfolio.get_wallet(currency)


@log_action("REGISTER")
def register_user(username: str, password: str) -> tuple[int, str]:
    username_v = validate_username(username)
    password_v = validate_password(password)

    db = _db()
    users = db.read_users()

    if any(u["username"] == username_v for u in users):
        raise ValueError(f"Имя пользователя '{username_v}' уже занято")

    user_id = _next_user_id(users)
    salt = make_salt()
    hashed = hash_password(password_v, salt)
    reg_date = now_iso()

    users.append(
        {
            "user_id": user_id,
            "username": username_v,
            "hashed_password": hashed,
            "salt": salt,
            "registration_date": reg_date,
        }
    )
    db.write_users(users)

    portfolios = db.read_portfolios()
    portfolios.append({"user_id": user_id, "wallets": {}})
    db.write_portfolios(portfolios)

    return user_id, username_v


@log_action("LOGIN")
def login_user(username: str, password: str) -> User:
    username_v = validate_username(username)
    password_v = validate_password(password)

    db = _db()
    users = db.read_users()

    found = None
    for u in users:
        if u["username"] == username_v:
            found = u
            break

    if found is None:
        raise ValueError(f"Пользователь '{username_v}' не найден")

    user = User(
        user_id=int(found["user_id"]),
        username=str(found["username"]),
        hashed_password=str(found["hashed_password"]),
        salt=str(found["salt"]),
        registration_date=str(found["registration_date"]),
    )

    if not user.verify_password(password_v):
        raise ValueError("Неверный пароль")

    return user


def load_portfolio(user_id: int) -> Portfolio:
    db = _db()
    portfolios = db.read_portfolios()

    found = None
    for p in portfolios:
        if int(p["user_id"]) == int(user_id):
            found = p
            break

    if found is None:
        raise ValueError("Портфель не найден")

    wallets_data: dict[str, Any] = found.get("wallets", {})
    wallets: dict[str, Wallet] = {}

    for code, w in wallets_data.items():
        code_u = str(code).upper()
        balance = w.get("balance", 0.0) if isinstance(w, dict) else 0.0
        wallets[code_u] = Wallet(code_u, balance)

    return Portfolio(int(user_id), wallets)


def save_portfolio(portfolio: Portfolio) -> None:
    db = _db()
    portfolios = db.read_portfolios()

    idx = None
    for i, p in enumerate(portfolios):
        if int(p["user_id"]) == int(portfolio.user_id):
            idx = i
            break

    if idx is None:
        raise ValueError("Портфель не найден")

    wallets_out: dict[str, Any] = {}
    for code, wallet in portfolio.wallets.items():
        wallets_out[code] = {"balance": wallet.balance}

    portfolios[idx] = {"user_id": portfolio.user_id, "wallets": wallets_out}
    db.write_portfolios(portfolios)


@log_action("GET_RATE")
def get_rate(from_currency: str, to_currency: str, max_age_seconds: int | None = None) -> dict[str, str]:
    """Возвращает курс валюты из локального кеша с учётом TTL."""
    from_c = normalize_currency_code(from_currency)
    to_c = normalize_currency_code(to_currency)

    get_currency(from_c)
    get_currency(to_c)

    ttl = int(_settings().get("RATES_TTL_SECONDS", 300))
    if max_age_seconds is None:
        max_age_seconds = ttl

    key = _pair_key(from_c, to_c)
    db = _db()
    rates: dict[str, Any] = db.read_rates()

    pairs = rates.get("pairs", {})
    if isinstance(pairs, dict) and key in pairs and isinstance(pairs[key], dict):
        updated_at = pairs[key].get("updated_at")
        rate = pairs[key].get("rate")
        source = pairs[key].get("source", "cache")

        if isinstance(updated_at, str) and isinstance(rate, (int, float)):
            age = (parse_iso(now_iso()) - parse_iso(updated_at)).total_seconds()
            if age <= max_age_seconds:
                return {
                    "pair": key,
                    "rate": str(rate),
                    "updated_at": updated_at,
                    "source": str(source),
                }

    raise ApiRequestError("Данные устарели или отсутствуют. Выполните update-rates.")


@log_action("BUY", verbose=True)
def buy_currency(user_id: int, currency: str, amount: float, base: str = "USD") -> dict[str, str]:
    """Покупка валюты с использованием курса из кеша."""
    cur = normalize_currency_code(currency)
    base_c = normalize_currency_code(base)

    get_currency(cur)
    get_currency(base_c)

    amount_f = validate_amount(amount)

    portfolio = load_portfolio(user_id)

    base_wallet = _ensure_wallet(portfolio, base_c)
    cur_wallet = _ensure_wallet(portfolio, cur)

    if cur == base_c:
        before = base_wallet.balance
        base_wallet.deposit(amount_f)
        after = base_wallet.balance
        save_portfolio(portfolio)
        return {
            "currency": cur,
            "amount": f"{amount_f:.4f}",
            "before": f"{before:.4f}",
            "after": f"{after:.4f}",
        }

    rate_info = get_rate(cur, base_c)
    rate = float(rate_info["rate"])
    cost = rate * amount_f

    usd_before = base_wallet.balance
    cur_before = cur_wallet.balance

    base_wallet.withdraw(cost)
    cur_wallet.deposit(amount_f)

    save_portfolio(portfolio)

    return {
        "currency": cur,
        "amount": f"{amount_f:.4f}",
        "before": f"{cur_before:.4f}",
        "after": f"{cur_wallet.balance:.4f}",
        "rate_pair": rate_info["pair"],
        "rate": rate_info["rate"],
        "estimated_value": f"{cost:.2f}",
        "base": base_c,
        "usd_before": f"{usd_before:.2f}",
        "usd_after": f"{base_wallet.balance:.2f}",
    }


@log_action("SELL", verbose=True)
def sell_currency(user_id: int, currency: str, amount: float, base: str = "USD") -> dict[str, str]:
    """Продажа валюты с конвертацией в базовую валюту."""
    cur = normalize_currency_code(currency)
    base_c = normalize_currency_code(base)

    get_currency(cur)
    get_currency(base_c)

    amount_f = validate_amount(amount)

    portfolio = load_portfolio(user_id)

    if cur not in portfolio.wallets:
        raise ValueError(f"У вас нет кошелька '{cur}'.")

    base_wallet = _ensure_wallet(portfolio, base_c)
    cur_wallet = portfolio.get_wallet(cur)

    if cur == base_c:
        before = base_wallet.balance
        base_wallet.withdraw(amount_f)
        after = base_wallet.balance
        save_portfolio(portfolio)
        return {
            "currency": cur,
            "amount": f"{amount_f:.4f}",
            "before": f"{before:.4f}",
            "after": f"{after:.4f}",
        }

    rate_info = get_rate(cur, base_c)
    rate = float(rate_info["rate"])
    revenue = rate * amount_f

    usd_before = base_wallet.balance
    cur_before = cur_wallet.balance

    cur_wallet.withdraw(amount_f)
    base_wallet.deposit(revenue)

    save_portfolio(portfolio)

    return {
        "currency": cur,
        "amount": f"{amount_f:.4f}",
        "before": f"{cur_before:.4f}",
        "after": f"{cur_wallet.balance:.4f}",
        "rate_pair": rate_info["pair"],
        "rate": rate_info["rate"],
        "estimated_value": f"{revenue:.2f}",
        "base": base_c,
        "usd_before": f"{usd_before:.2f}",
        "usd_after": f"{base_wallet.balance:.2f}",
    }


def show_portfolio(user_id: int, base: str = "USD") -> dict[str, object]:
    base_c = normalize_currency_code(base)
    get_currency(base_c)

    portfolio = load_portfolio(user_id)

    rows: list[dict[str, str]] = []
    total = 0.0

    for code, wallet in sorted(portfolio.wallets.items()):
        get_currency(code)
        bal = wallet.balance

        if code == base_c:
            value_base = bal
        else:
            rate_info = get_rate(code, base_c)
            value_base = bal * float(rate_info["rate"])

        rows.append(
            {
                "currency": code,
                "balance": f"{bal:.4f}" if code in {"BTC", "ETH"} else f"{bal:.2f}",
                "value_in_base": f"{value_base:.2f}",
                "base": base_c,
            }
        )
        total += value_base

    return {
        "base": base_c,
        "rows": rows,
        "total": f"{total:.2f}",
    }
