from abc import ABC, abstractmethod
from typing import Dict
from .exceptions import CurrencyNotFoundError


class Currency(ABC):
    def __init__(self, name: str, code: str):
        self._validate_code(code)
        self._validate_name(name)
        self._name = name
        self._code = code.upper()

    def _validate_code(self, code: str):
        if not isinstance(code, str) or not 2 <= len(code) <= 5:
            raise ValueError(
                "Код валюты должен быть строкой длиной 2-5 символов")
        if not code.isalnum() or ' ' in code:
            raise ValueError("Код валюты не должен содержать пробелы")

    def _validate_name(self, name: str):
        if not name or not isinstance(name, str) or not name.strip():
            raise ValueError("Название валюты не может быть пустым")

    @property
    def name(self) -> str:
        return self._name

    @property
    def code(self) -> str:
        return self._code

    @abstractmethod
    def get_display_info(self) -> str:
        pass

    def __str__(self) -> str:
        return self.get_display_info()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', code='{
            self.code}')"


class FiatCurrency(Currency):
    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        self._issuing_country = issuing_country

    @property
    def issuing_country(self) -> str:
        return self._issuing_country

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {
            self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    def __init__(self, name: str, code: str, algorithm: str,
                 market_cap: float = 0.0):
        super().__init__(name, code)
        self._algorithm = algorithm
        self._market_cap = market_cap

    @property
    def algorithm(self) -> str:
        return self._algorithm

    @property
    def market_cap(self) -> float:
        return self._market_cap

    def get_display_info(self) -> str:
        mcap_str = f"{self.market_cap:.2e}" if self.market_cap > 1e6 else f"{
            self.market_cap:.2f}"
        return f"[CRYPTO] {self.code} — {
            self.name} (Algo: {self.algorithm}, MCAP: {mcap_str})"


# Реестр валют
_currency_registry: Dict[str, Currency] = {}


def register_currency(currency: Currency):
    """Регистрирует валюту в реестре"""
    _currency_registry[currency.code] = currency


def get_currency(code: str) -> Currency:
    """Возвращает валюту по коду"""
    code = code.upper()
    if code not in _currency_registry:
        raise CurrencyNotFoundError(code)
    return _currency_registry[code]


def get_all_currencies() -> Dict[str, Currency]:
    """Возвращает все зарегистрированные валюты"""
    return _currency_registry.copy()

# Инициализация реестра стандартными валютами


def _initialize_currencies():
    """Инициализирует реестр стандартными валютами"""
    # Фиатные валюты
    register_currency(FiatCurrency("US Dollar", "USD", "United States"))
    register_currency(FiatCurrency("Euro", "EUR", "Eurozone"))
    register_currency(FiatCurrency("Russian Ruble", "RUB", "Russia"))
    register_currency(FiatCurrency("British Pound", "GBP", "United Kingdom"))
    register_currency(FiatCurrency("Japanese Yen", "JPY", "Japan"))

    # Криптовалюты
    register_currency(CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12))
    register_currency(CryptoCurrency("Ethereum", "ETH", "Ethash", 4.5e11))
    register_currency(CryptoCurrency("Litecoin", "LTC", "Scrypt", 6.5e9))
    register_currency(CryptoCurrency("Cardano", "ADA", "Ouroboros", 1.5e10))


# Автоматическая инициализация при импорте
_initialize_currencies()
