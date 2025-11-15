import json
import os
import threading
from typing import Dict, List, Any, Optional
from ..core.exceptions import ValutaTradeError

class DatabaseError(ValutaTradeError):
    """Ошибка работы с базой данных"""
    pass

class DatabaseManager:
    """
    Singleton менеджер базы данных для безопасных операций с JSON-хранилищем.
    Обеспечивает атомарные операции чтение→модификация→запись.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, data_dir: str = "data"):
        if not self._initialized:
            self.data_dir = data_dir
            self._locks: Dict[str, threading.Lock] = {}  # Локи для каждого файла
            self._initialized = True
    
    def _get_file_lock(self, filename: str) -> threading.Lock:
        """Возвращает lock для конкретного файла"""
        with self._lock:
            if filename not in self._locks:
                self._locks[filename] = threading.Lock()
            return self._locks[filename]
    
    def _get_file_path(self, filename: str) -> str:
        """Возвращает полный путь к файлу"""
        return os.path.join(self.data_dir, filename)
    
    def read_data(self, filename: str) -> List[Dict[str, Any]]:
        """
        Безопасное чтение данных из JSON файла.
        
        Args:
            filename: Имя файла (например, 'users.json')
            
        Returns:
            Список данных из файла
            
        Raises:
            DatabaseError: Если произошла ошибка при чтении
        """
        file_path = self._get_file_path(filename)
        file_lock = self._get_file_lock(filename)
        
        with file_lock:
            try:
                if not os.path.exists(file_path):
                    return []
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
                    
            except json.JSONDecodeError as e:
                raise DatabaseError(f"Ошибка формата JSON в файле {filename}: {e}")
            except Exception as e:
                raise DatabaseError(f"Ошибка чтения файла {filename}: {e}")
    
    def write_data(self, filename: str, data: List[Dict[str, Any]]) -> None:
        """
        Безопасная запись данных в JSON файл.
        
        Args:
            filename: Имя файла
            data: Данные для записи
            
        Raises:
            DatabaseError: Если произошла ошибка при записи
        """
        file_path = self._get_file_path(filename)
        file_lock = self._get_file_lock(filename)
        
        with file_lock:
            try:
                # Создаем директорию если не существует
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Атомарная запись во временный файл + переименование
                temp_path = file_path + '.tmp'
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                # Атомарная замена файла
                os.replace(temp_path, file_path)
                
            except Exception as e:
                # Удаляем временный файл в случае ошибки
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise DatabaseError(f"Ошибка записи в файл {filename}: {e}")
    
    def atomic_update(self, filename: str, update_func: callable) -> Any:
        """
        Атомарное обновление данных: чтение→модификация→запись.
        
        Args:
            filename: Имя файла
            update_func: Функция для модификации данных
                        Принимает текущие данные, возвращает модифицированные
            
        Returns:
            Результат выполнения update_func
            
        Raises:
            DatabaseError: Если произошла ошибка
        """
        file_lock = self._get_file_lock(filename)
        
        with file_lock:
            try:
                # Чтение
                data = self.read_data(filename)
                
                # Модификация
                result = update_func(data)
                
                # Запись
                self.write_data(filename, data)
                
                return result
                
            except Exception as e:
                if not isinstance(e, DatabaseError):
                    raise DatabaseError(f"Ошибка атомарного обновления {filename}: {e}")
                raise
    
    def find_one(self, filename: str, condition: callable) -> Optional[Dict[str, Any]]:
        """
        Поиск одного элемента по условию.
        
        Args:
            filename: Имя файла
            condition: Функция-условие (возвращает bool)
            
        Returns:
            Найденный элемент или None
        """
        data = self.read_data(filename)
        return next((item for item in data if condition(item)), None)
    
    def find_all(self, filename: str, condition: callable = None) -> List[Dict[str, Any]]:
        """
        Поиск всех элементов по условию.
        
        Args:
            filename: Имя файла
            condition: Опциональная функция-условие
            
        Returns:
            Список найденных элементов
        """
        data = self.read_data(filename)
        if condition:
            return [item for item in data if condition(item)]
        return data
    
    def insert(self, filename: str, item: Dict[str, Any]) -> None:
        """
        Вставка нового элемента.
        
        Args:
            filename: Имя файла
            item: Элемент для вставки
        """
        def update_func(data):
            data.append(item)
            return item
        
        self.atomic_update(filename, update_func)
    
    def update_one(self, filename: str, condition: callable, updates: Dict[str, Any]) -> bool:
        """
        Обновление одного элемента по условию.
        
        Args:
            filename: Имя файла
            condition: Функция-условие
            updates: Обновления для элемента
            
        Returns:
            True если элемент был обновлен, False если не найден
        """
        def update_func(data):
            for item in data:
                if condition(item):
                    item.update(updates)
                    return True
            return False
        
        return self.atomic_update(filename, update_func)
    
    def delete_one(self, filename: str, condition: callable) -> bool:
        """
        Удаление одного элемента по условию.
        
        Args:
            filename: Имя файла
            condition: Функция-условие
            
        Returns:
            True если элемент был удален, False если не найден
        """
        def update_func(data):
            for i, item in enumerate(data):
                if condition(item):
                    del data[i]
                    return True
            return False
        
        return self.atomic_update(filename, update_func)
    
    def get_next_id(self, filename: str, id_field: str = "id") -> int:
        """
        Генерация следующего ID для файла.
        
        Args:
            filename: Имя файла
            id_field: Поле содержащее ID
            
        Returns:
            Следующий ID
        """
        data = self.read_data(filename)
        if not data:
            return 1
        
        max_id = max(item.get(id_field, 0) for item in data)
        return max_id + 1


# Глобальный экземпляр для использования во всем приложении
db = DatabaseManager()
