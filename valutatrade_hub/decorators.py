from __future__ import annotations

import inspect
import logging
from functools import wraps
from typing import Any, Callable

from valutatrade_hub.core.utils import now_iso


def log_action(action: str, verbose: bool = False) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = logging.getLogger("valutatrade")
            ts = now_iso()

            bound = inspect.signature(func).bind_partial(*args, **kwargs)
            data = bound.arguments

            user = data.get("username", data.get("user_id"))
            currency = data.get("currency", data.get("currency_code"))
            if currency is None and "from_currency" in data and "to_currency" in data:
                currency = f"{data['from_currency']}->{data['to_currency']}"

            amount = data.get("amount")
            base = data.get("base")
            rate = data.get("rate")

            try:
                result = func(*args, **kwargs)
                msg = f"{ts} {action} user='{user}' currency='{currency}' amount={amount} rate={rate} base='{base}' result=OK"
                logger.info(msg)
                if verbose:
                    logger.info(f"{ts} {action} verbose result={result}")
                return result
            except Exception as e:
                msg = (
                    f"{ts} {action} user='{user}' currency='{currency}' amount={amount} "
                    f"rate={rate} base='{base}' result=ERROR error_type={type(e).__name__} error_message='{e}'"
                )
                logger.info(msg)
                raise

        return wrapper

    return decorator
