from __future__ import annotations

import shlex

from prettytable import PrettyTable
from valutatrade_hub.core.exceptions import CurrencyNotFoundError, ApiRequestError, InsufficientFundsError
from valutatrade_hub.core.currencies import list_supported_codes
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.core.usecases import (
    register_user,
    login_user,
    get_rate,
    buy_currency,
    sell_currency,
    show_portfolio,
)


def _parse_kv(parts: list[str]) -> dict[str, str]:
    args: dict[str, str] = {}
    i = 0
    while i < len(parts):
        key = parts[i]
        if not key.startswith("--"):
            raise ValueError(f"Неизвестный аргумент: {key}")
        if i + 1 >= len(parts):
            raise ValueError(f"Нет значения для {key}")
        args[key] = parts[i + 1]
        i += 2
    return args


def _print_help() -> None:
    print("Команды:")
    print("  register --username <str> --password <str>")
    print("  login --username <str> --password <str>")
    print("  show-portfolio [--base <str>]")
    print("  buy --currency <str> --amount <float>")
    print("  sell --currency <str> --amount <float>")
    print("  get-rate --from <str> --to <str>")
    print("  exit")


def run() -> None:
    setup_logging()
    current_user_id: int | None = None
    current_username: str | None = None

    print("ValutaTrade Hub CLI")
    print("Type 'help' to see available commands.")

    while True:
        try:
            raw = input("> ").strip()
        except EOFError:
            print()
            break

        if raw == "":
            continue

        try:
            tokens = shlex.split(raw)
        except ValueError:
            print("Некорректная команда")
            continue

        cmd = tokens[0]
        parts = tokens[1:]

        if cmd in {"exit", "quit"}:
            break

        if cmd == "help":
            _print_help()
            continue

        try:
            if cmd == "register":
                args = _parse_kv(parts)
                uid, uname = register_user(args["--username"], args["--password"])
                print(f"Пользователь '{uname}' зарегистрирован (id={uid}). Войдите: login --username {uname} --password ****")

            elif cmd == "login":
                args = _parse_kv(parts)
                user = login_user(args["--username"], args["--password"])
                current_user_id = user.user_id
                current_username = user.username
                print(f"Вы вошли как '{current_username}'")

            elif cmd == "show-portfolio":
                if current_user_id is None:
                    print("Сначала выполните login")
                    continue
                args = _parse_kv(parts) if parts else {}
                base = args.get("--base", "USD")
                data = show_portfolio(current_user_id, base)

                table = PrettyTable()
                table.field_names = ["Currency", "Balance", f"Value ({data['base']})"]
                for row in data["rows"]:
                    table.add_row([row["currency"], row["balance"], row["value_in_base"]])

                print(f"Портфель пользователя '{current_username}' (база: {data['base']}):")
                if not data["rows"]:
                    print("Портфель пуст")
                else:
                    print(table)
                    print(f"ИТОГО: {data['total']} {data['base']}")

            elif cmd == "buy":
                if current_user_id is None:
                    print("Сначала выполните login")
                    continue
                args = _parse_kv(parts)
                res = buy_currency(current_user_id, args["--currency"], float(args["--amount"]))
                print(f"Покупка выполнена: {res['amount']} {res['currency']}")
                print(f"- {res['currency']}: было {res['before']} → стало {res['after']}")
                if "rate_pair" in res:
                    print(f"Списано: {res['estimated_value']} {res['base']} (USD: {res['usd_before']} → {res['usd_after']})")

            elif cmd == "sell":
                if current_user_id is None:
                    print("Сначала выполните login")
                    continue
                args = _parse_kv(parts)
                res = sell_currency(current_user_id, args["--currency"], float(args["--amount"]))
                print(f"Продажа выполнена: {res['amount']} {res['currency']}")
                print(f"- {res['currency']}: было {res['before']} → стало {res['after']}")
                if "rate_pair" in res:
                    print(f"Начислено: {res['estimated_value']} {res['base']} (USD: {res['usd_before']} → {res['usd_after']})")

            elif cmd == "get-rate":
                args = _parse_kv(parts)
                info = get_rate(args["--from"], args["--to"])
                fr, to = info["pair"].split("_", 1)
                rate = float(info["rate"])
                print(f"Курс {fr}→{to}: {rate} (обновлено: {info['updated_at']})")
                if rate != 0:
                    inv = 1 / rate
                    print(f"Обратный курс {to}→{fr}: {inv:.8f}")

            else:
                print("Неизвестная команда. help")

        except KeyError:
            print("Не хватает аргументов")
        except ValueError as e:
            print(str(e))
        except InsufficientFundsError as e:
            print(str(e))
        except CurrencyNotFoundError as e:
            print(str(e))
            print("Подсказка: help get-rate")
            print("Поддерживаемые коды:", ", ".join(list_supported_codes()))
        except ApiRequestError as e:
            print(str(e))
            print("Повторите попытку позже или проверьте сеть")
        except ValueError as e:
            print(str(e))
