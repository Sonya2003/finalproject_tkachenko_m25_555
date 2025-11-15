class ValutaTradeError(Exception):
    """Базовое исключение для ValutaTrade Hub"""
    pass

class InsufficientFundsError(ValutaTradeError):
    def __init__(self, available: float, required: float, code: str):
        self.available = available
        self.required = required
        self.code = code
        super().__init__(f"Недостаточно средств: доступно {available} {code}, требуется {required} {code}")

class CurrencyNotFoundError(ValutaTradeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")

class ApiRequestError(ValutaTradeError):
    def __init__(self, reason: str = "неизвестная ошибка"):
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
