# ValutaTrade Hub

Консольное приложение для управления портфелем валют (фиат и крипто) и получения курсов из локального кеша.
Курсы обновляются отдельным Parser Service (CoinGecko + ExchangeRate-API).

## Структура проекта

- `valutatrade_hub/core/` — доменные модели и бизнес-логика
- `valutatrade_hub/cli/` — CLI интерфейс
- `valutatrade_hub/parser_service/` — обновление курсов и сохранение кеша/истории
- `valutatrade_hub/infra/` — настройки и доступ к JSON-хранилищу
- `data/` — данные: `users.json`, `portfolios.json`, `rates.json`, `exchange_rates.json`
- `logs/actions.log` — журнал операций

## Установка

make install

## Установка

make project
# или
poetry run project

## Команды

Регистрация:
register --username <str> --password <str>

Вход:
login --username <str> --password <str>

Портфель:
show-portfolio [--base <str>]

Покупка/продажа:
buy --currency <str> --amount <float>
sell --currency <str> --amount <float>

Обновить курсы:
update-rates [--source coingecko|exchangerate]

Показать курсы из кеша:
show-rates [--currency <str>] [--top <int>] [--base <str>]

Курс:
get-rate --from <str> --to <str>

## Парсер
CoinGecko — криптовалюты - без ключа
ExchangeRate-API — фиатные валюты - нужен ключ формата EXCHANGERATE_API_KEY="ВАШ_API_КЛЮЧ" poetry run project

## Demo
[![asciinema demo](https://asciinema.org/a/wBTMyGp1MwGcg13a.svg)](https://asciinema.org/a/wBTMyGp1MwGcg13a)
