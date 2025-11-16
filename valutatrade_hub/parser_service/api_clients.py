import requests
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
import time
from .config import ParserConfig
from ..core.exceptions import ApiRequestError

logger = logging.getLogger(__name__)


class BaseApiClient(ABC):
    """Абстрактный базовый класс для API клиентов"""

    def __init__(self, config: ParserConfig):
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    def fetch_rates(self) -> Dict[str, float]:
        """Получает курсы валют от API"""
        pass

    def _make_request(
            self, url: str, params: Dict[str, Any] = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """Выполняет HTTP запрос с обработкой ошибок и повторными попытками"""
        for attempt in range(self.config.MAX_RETRIES):
            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.config.REQUEST_TIMEOUT
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout:
                logger.warning(f"{self.name} timeout (attempt {
                               attempt + 1}/{self.config.MAX_RETRIES})")
                if attempt < self.config.MAX_RETRIES - 1:
                    time.sleep(self.config.RETRY_DELAY)
                    continue
                raise ApiRequestError(f"{self.name}: Request timeout")

            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:  # Rate limit
                    logger.warning(f"{self.name} rate limit (attempt {
                                   attempt + 1}/{self.config.MAX_RETRIES})")
                    if attempt < self.config.MAX_RETRIES - 1:
                        time.sleep(self.config.RETRY_DELAY * 2)
                        continue
                raise ApiRequestError(f"{self.name}: HTTP {
                                      response.status_code} - {str(e)}")

            except requests.exceptions.RequestException as e:
                logger.error(f"{self.name} network error: {e}")
                if attempt < self.config.MAX_RETRIES - 1:
                    time.sleep(self.config.RETRY_DELAY)
                    continue
                raise ApiRequestError(f"{self.name}: Network error - {str(e)}")

            except ValueError as e:
                logger.error(f"{self.name} JSON parse error: {e}")
                raise ApiRequestError(f"{self.name}: Invalid JSON response")


class CoinGeckoClient(BaseApiClient):
    """Клиент для CoinGecko API"""

    def fetch_rates(self) -> Dict[str, float]:
        """Получает курсы криптовалют"""
        logger.info("Fetching crypto rates from CoinGecko...")

        # Формируем список ID криптовалют
        crypto_ids = [
            self.config.CRYPTO_ID_MAP[currency]
            for currency in self.config.CRYPTO_CURRENCIES
            if currency in self.config.CRYPTO_ID_MAP
        ]

        if not crypto_ids:
            logger.warning("No valid crypto currencies configured")
            return {}

        params = {
            'ids': ','.join(crypto_ids),
            'vs_currencies': self.config.BASE_CURRENCY.lower()
        }

        data = self._make_request(self.config.COINGECKO_URL, params)

        # Преобразуем ответ в стандартный формат
        rates = {}
        for currency in self.config.CRYPTO_CURRENCIES:
            if currency in self.config.CRYPTO_ID_MAP:
                crypto_id = self.config.CRYPTO_ID_MAP[currency]
                if crypto_id in data and self.config.BASE_CURRENCY.lower(
                ) in data[crypto_id]:
                    rate_key = f"{currency}_{self.config.BASE_CURRENCY}"
                    rates[rate_key] = float(
                        data[crypto_id][self.config.BASE_CURRENCY.lower()])

        logger.info(f"CoinGecko: successfully fetched {
                    len(rates)} crypto rates")
        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Клиент для ExchangeRate-API"""

    def fetch_rates(self) -> Dict[str, float]:
        """Получает курсы фиатных валют"""
        logger.info("Fetching fiat rates from ExchangeRate-API...")

        if self.config.EXCHANGERATE_API_KEY == "demo-key":
            logger.warning("Using demo API key - rates may be outdated")

        url = f"{self.config.EXCHANGERATE_API_URL}/{
            self.config.EXCHANGERATE_API_KEY}/latest/{self.config.BASE_CURRENCY}"

        data = self._make_request(url)

        # Проверяем успешность запроса
        if data.get('result') != 'success':
            error_type = data.get('error-type', 'Unknown error')
            raise ApiRequestError(f"ExchangeRate-API: {error_type}")

        rates = {}
        conversion_rates = data.get('conversion_rates', {})

        for currency in self.config.FIAT_CURRENCIES:
            if currency in conversion_rates:
                rate_key = f"{currency}_{self.config.BASE_CURRENCY}"
                rates[rate_key] = float(conversion_rates[currency])

        # Добавляем базовую валюту
        base_key = f"{self.config.BASE_CURRENCY}_{self.config.BASE_CURRENCY}"
        rates[base_key] = 1.0

        logger.info(
            f"ExchangeRate-API: successfully fetched {len(rates)} fiat rates")
        return rates
