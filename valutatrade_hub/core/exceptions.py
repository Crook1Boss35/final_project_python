class InsufficientFundsError(Exception):
    """Недостаточно средств."""

    def __init__(self, available: float, required: float, code: str) -> None:
        msg = f"Недостаточно средств: доступно {available} {code}, требуется {required} {code}"
        super().__init__(msg)


class CurrencyNotFoundError(Exception):
    """Неизвестная валюта."""

    def __init__(self, code: str) -> None:
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(Exception):
    """Сбой API."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
