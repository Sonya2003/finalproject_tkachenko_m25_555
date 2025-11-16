import logging
import datetime
from typing import Dict, List, Any
from .config import ParserConfig
from .api_clients import CoinGeckoClient, ExchangeRateApiClient
from .storage import RatesStorage
from ..core.exceptions import ApiRequestError

logger = logging.getLogger(__name__)


class RatesUpdater:
    """Координатор обновления курсов валют"""

    def __init__(self, config: ParserConfig = None):
        self.config = config or ParserConfig()
        self.storage = RatesStorage(self.config)

        # Инициализируем клиенты
        self.clients = {
            'coingecko': CoinGeckoClient(self.config),
            'exchangerate': ExchangeRateApiClient(self.config)
        }

    def run_update(self, sources: List[str] = None) -> Dict[str, Any]:
        """Запускает обновление курсов"""
        logger.info("Starting rates update...")

        if sources is None:
            sources = list(self.clients.keys())

        all_rates = {}
        update_stats = {
            'total_rates': 0,
            'updated_rates': 0,
            'historical_records': 0,
            'errors': [],
            'sources_processed': []
        }

        for source_name in sources:
            if source_name not in self.clients:
                error_msg = f"Unknown source: {source_name}"
                logger.warning(error_msg)
                update_stats['errors'].append(error_msg)
                continue

            try:
                client = self.clients[source_name]
                logger.info(f"Fetching from {source_name}...")

                rates = client.fetch_rates()
                all_rates.update(rates)

                # Сохраняем в кеш
                cache_updated = self.storage.save_current_rates(
                    rates, source_name)
                # Сохраняем в историю
                history_saved = self.storage.save_historical_record(
                    rates, source_name)

                update_stats['total_rates'] += len(rates)
                update_stats['updated_rates'] += cache_updated
                update_stats['historical_records'] += history_saved
                update_stats['sources_processed'].append(source_name)

                logger.info(f"{source_name}: {len(rates)} rates, {
                            cache_updated} updated in cache, {history_saved} historical records")

            except ApiRequestError as e:
                error_msg = f"{source_name}: {str(e)}"
                logger.error(f"{error_msg}")
                update_stats['errors'].append(error_msg)
            except Exception as e:
                error_msg = f"{source_name}: Unexpected error - {str(e)}"
                logger.error(f"{error_msg}")
                update_stats['errors'].append(error_msg)

        # Добавляем метаданные
        update_stats.update({
            "success": len(update_stats['errors']) == 0,
            "updated_at": datetime.datetime.now().isoformat(),
            "sources_count": len(update_stats['sources_processed'])
        })

        if update_stats['errors']:
            logger.warning(f"Update completed with {
                           len(update_stats['errors'])} errors")
        else:
            logger.info(f"Update successful! Processed {update_stats['sources_count']} sources, {
                        update_stats['total_rates']} total rates")

        return update_stats

    def get_update_status(self) -> Dict[str, Any]:
        """Возвращает статус последнего обновления"""
        rates_data = self.storage.load_current_rates()

        if not rates_data:
            return {
                "status": "empty",
                "message": "No rates data available"
            }

        # Проверяем свежесть данных
        sample_rate = next(iter(rates_data.keys())) if rates_data else None
        if sample_rate:
            freshness = self.storage.get_rate_freshness(sample_rate)
            if freshness < 0:
                status = "stale"
            elif freshness > self.config.RATES_TTL:
                status = "outdated"
            else:
                status = "fresh"
        else:
            status = "unknown"

        return {
            "status": status,
            "total_rates": len(rates_data),
            "rates_ttl": self.config.RATES_TTL,
            "sources": list(set(rate.get('source', 'unknown') for rate in rates_data.values()))
        }
