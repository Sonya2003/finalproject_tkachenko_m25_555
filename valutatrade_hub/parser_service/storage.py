import datetime
from typing import Dict, Any
from ..infra.database import db


class RatesStorage:
    """Хранилище для курсов валют"""

    def __init__(self, config):
        self.config = config

    def save_current_rates(self, rates: Dict[str, float], source: str) -> int:
        """Сохраняет текущие курсы в rates.json (кеш)"""
        current_time = datetime.datetime.now().isoformat()

        # Загружаем существующие курсы
        existing_rates = db.read_data("rates.json")
        if not isinstance(existing_rates, dict):
            existing_rates = {}

        updated_count = 0
        for rate_key, rate_value in rates.items():
            # Обновляем только если курс новый или обновлен
            if (rate_key not in existing_rates or
                existing_rates[rate_key].get('source') != source or
                    existing_rates[rate_key].get('rate') != rate_value):

                existing_rates[rate_key] = {
                    "rate": rate_value,
                    "updated_at": current_time,
                    "source": source
                }
                updated_count += 1

        if updated_count > 0:
            db.write_data("rates.json", existing_rates)

        return updated_count

    def save_historical_record(
            self, rates: Dict[str, float], source: str) -> int:
        """Сохраняет историческую запись в exchange_rates.json"""
        current_time = datetime.datetime.now().isoformat()
        current_utc = datetime.datetime.now(
            datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        historical_data = db.read_data("exchange_rates.json")
        if not isinstance(historical_data, list):
            historical_data = []

        saved_count = 0
        for rate_key, rate_value in rates.items():
            # Создаем уникальный ID согласно ТЗ
            record_id = f"{rate_key}_{current_utc.replace(
                ':', '').replace('-', '').replace('T', '_')}"

            record = {
                "id": record_id,
                "from_currency": rate_key.split('_')[0],
                "to_currency": rate_key.split('_')[1],
                "rate": rate_value,
                "timestamp": current_utc,
                "source": source,
                "created_at": current_time
            }

            # Проверяем дубликаты
            if not any(r.get('id') == record_id for r in historical_data):
                historical_data.append(record)
                saved_count += 1

        if saved_count > 0:
            db.write_data("exchange_rates.json", historical_data)

        return saved_count

    def load_current_rates(self) -> Dict[str, Any]:
        """Загружает текущие курсы из кеша"""
        rates_data = db.read_data("rates.json")
        if not isinstance(rates_data, dict):
            return {}
        return rates_data

    def get_rate_freshness(self, rate_key: str) -> int:
        """Возвращает свежесть курса в секундах"""
        rates_data = self.load_current_rates()
        if rate_key not in rates_data:
            return -1  # Курс не найден

        updated_at_str = rates_data[rate_key].get('updated_at')
        if not updated_at_str:
            return -1

        try:
            updated_at = datetime.datetime.fromisoformat(updated_at_str)
            now = datetime.datetime.now()
            return int((now - updated_at).total_seconds())
        except (ValueError, TypeError):
            return -1
