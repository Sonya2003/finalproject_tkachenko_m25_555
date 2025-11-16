import os
import json
from typing import Any, Dict


class SettingsLoader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsLoader, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._config = self._load_config()
            self._initialized = True

    def _load_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию из различных источников"""
        base_config = {
            "data_dir": "data",
            "rates_ttl_seconds": 300,  # 5 минут
            "default_base_currency": "USD",
            "log_level": "INFO",
            "log_file": "logs/actions.log",
            "max_log_size_mb": 10,
            "backup_count": 5
        }

        config_file = "config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    base_config.update(user_config)
            except Exception:
                pass

        return base_config

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает значение настройки по ключу"""
        return self._config.get(key, default)

    def reload(self):
        """Перезагружает конфигурацию"""
        self._config = self._load_config()

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __contains__(self, key: str) -> bool:
        return key in self._config


settings = SettingsLoader()
