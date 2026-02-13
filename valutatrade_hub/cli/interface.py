from __future__ import annotations

import shlex

from prettytable import PrettyTable

from valutatrade_hub.core.currencies import list_supported_codes
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import (
    buy_currency,
    get_rate,
    login_user,
    register_user,
    sell_currency,
    show_portfolio,
)
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.parser_service.api_clients import CoinGeckoClient, ExchangeRateApiClient
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater

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
    print("  update-rates [--source <coingecko|exchangerate>]")
    print("  show-rates [--currency <str>] [--top <int>] [--base <str>]")
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

            elif cmd == "update-rates":
                args = _parse_kv(parts) if parts else {}
                source = args.get("--source")

                if source is not None and source not in {"coingecko", "exchangerate"}:
                    raise ValueError("source должен быть: coingecko или exchangerate")

                config = ParserConfig()
                storage = RatesStorage()
                clients = [
                    CoinGeckoClient(config),
                    ExchangeRateApiClient(config),
                ]
                updater = RatesUpdater(clients, storage)

                result = updater.run_update(source=source)
                if result["errors"]:
                    for err in result["errors"]:
                        print(f"ERROR: {err}")

                if result["updated_count"] == 0 and result["errors"]:
                    print("Обновление завершилось с ошибками. Подробности в логах.")
                elif result["errors"]:
                    print("Обновление завершилось с ошибками, но часть данных обновлена.")
                else:
                    print("Обновление успешно.")

                print(f"Всего обновлено пар: {result['updated_count']}")
                print(f"Last refresh: {result['last_refresh']}")

            elif cmd == "show-rates":
                args = _parse_kv(parts) if parts else {}
                currency = args.get("--currency")
                top_raw = args.get("--top")
                base = args.get("--base")

                top: int | None = None
                if top_raw is not None:
                    top = int(top_raw)
                    if top <= 0:
                        raise ValueError("--top должен быть > 0")

                storage = RatesStorage()
                cache = storage.read_cache()
                pairs = cache.get("pairs", {})
                last_refresh = cache.get("last_refresh")

                if not pairs:
                    print("Локальный кеш курсов пуст. Выполните 'update-rates'.")
                    continue

                items = []
                for pair, data in pairs.items():
                    if base and not pair.endswith(f"_{base.upper()}"):
                        continue
                    if currency:
                        cur = currency.upper()
                        if not (pair.startswith(f"{cur}_") or pair.endswith(f"_{cur}")):
                            continue
                    items.append((pair, data))

                if not items:
                    if currency:
                        print(f"Курс для '{currency.upper()}' не найден в кеше.")
                    else:
                        print("Нет данных по заданным фильтрам.")
                    continue

                if top is not None:
                    items.sort(key=lambda x: float(x[1]["rate"]), reverse=True)
                    items = items[:top]
                else:
                    items.sort(key=lambda x: x[0])

                table = PrettyTable()
                table.field_names = ["Pair", "Rate", "Updated at", "Source"]
                for pair, data in items:
                    table.add_row([pair, data["rate"], data["updated_at"], data["source"]])

                print(f"Rates from cache (last refresh: {last_refresh}):")
                print(table)


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
