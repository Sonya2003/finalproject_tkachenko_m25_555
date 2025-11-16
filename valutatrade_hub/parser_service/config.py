import os
from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass
class ParserConfig:
    """Конфигурация для Parser Service"""

    # API Keys (из переменных окружения)
    EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY", "demo-key")

    # Endpoints
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # Currencies
    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: Tuple[str, ...] = (
        "EUR", "GBP", "RUB", "JPY", "CNY", "CHF", "CAD", "AUD")
    CRYPTO_CURRENCIES: Tuple[str, ...] = (
        "BTC", "ETH", "SOL", "ADA", "DOT", "BNB", "XRP", "DOGE")

    # CoinGecko ID mapping
    CRYPTO_ID_MAP: Dict[str, str] = field(default_factory=lambda: {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "ADA": "cardano",
        "DOT": "polkadot",
        "BNB": "binancecoin",
        "XRP": "ripple",
        "DOGE": "dogecoin"
    })

    # File paths
    RATES_FILE_PATH: str = "data/rates.json"
    HISTORY_FILE_PATH: str = "data/exchange_rates.json"

    # Network settings
    REQUEST_TIMEOUT: int = 10
    RATES_TTL: int = 300  # 5 minutes

    # Update settings
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2

    # Scheduler settings (в минутах)
    UPDATE_INTERVAL: int = 5
