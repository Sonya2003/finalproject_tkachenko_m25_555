import json
import os
from typing import List, Dict, Any
import datetime

def load_json_data(file_path: str) -> List[Dict[str, Any]]:
    """Загружает данные из JSON файла"""
    if not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_json_data(file_path: str, data: List[Dict[str, Any]]):
    """Сохраняет данные в JSON файл"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_next_id(data: List[Dict[str, Any]], key: str = "user_id") -> int:
    """Генерирует следующий ID"""
    if not data:
        return 1
    return max(item.get(key, 0) for item in data) + 1

def validate_currency_code(currency_code: str) -> bool:
    """Проверяет валидность кода валюты"""
    return bool(currency_code and isinstance(currency_code, str) and currency_code.strip())

def validate_amount(amount: float) -> bool:
    """Проверяет валидность суммы"""
    return isinstance(amount, (int, float)) and amount > 0

def format_currency_amount(amount: float, currency: str) -> str:
    """Форматирует сумму валюты для вывода"""
    if currency in ['BTC', 'ETH']:
        return f"{amount:.8f}"
    else:
        return f"{amount:.2f}"
