from .exceptions import InsufficientFundsError
import hashlib
import datetime
import secrets
from typing import Dict, Any, Optional

class User:
    def __init__(self, user_id: int, username: str, password: str, 
                 salt: str = None, registration_date: datetime.datetime = None):
        self.__user_id = user_id
        self.username = username  # Использует сеттер
        self.__salt = salt or self._generate_salt()
        self.__hashed_password = self._hash_password(password)
        self.__registration_date = registration_date or datetime.datetime.now()
    
    def _generate_salt(self) -> str:
        """Генерация случайной соли"""
        return secrets.token_hex(16)
    
    def _hash_password(self, password: str) -> str:
        """Хеширование пароля с солью"""
        return hashlib.sha256((password + self.__salt).encode()).hexdigest()
    
    # Геттеры
    @property
    def user_id(self) -> int:
        return self.__user_id
    
    @property
    def username(self) -> str:
        return self.__username
    
    @username.setter
    def username(self, value: str):
        if not value or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self.__username = value.strip()
    
    @property
    def hashed_password(self) -> str:
        return self.__hashed_password
    
    @property
    def salt(self) -> str:
        return self.__salt
    
    @property
    def registration_date(self) -> datetime.datetime:
        return self.__registration_date
    
    
    def get_user_info(self) -> Dict[str, Any]:
        """Возвращает информацию о пользователе (без пароля)"""
        return {
            "user_id": self.__user_id,
            "username": self.__username,
            "registration_date": self.__registration_date.isoformat()
        }
    
    def change_password(self, new_password: str):
        """Изменяет пароль пользователя"""
        if len(new_password) < 4:
            raise ValueError("Пароль должен содержать не менее 4 символов")
        
        self.__salt = self._generate_salt()
        self.__hashed_password = self._hash_password(new_password)
    
    def verify_password(self, password: str) -> bool:
        """Проверяет введённый пароль"""
        return self.__hashed_password == self._hash_password(password)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует объект в словарь для сохранения в JSON"""
        return {
            "user_id": self.__user_id,
            "username": self.__username,
            "hashed_password": self.__hashed_password,
            "salt": self.__salt,
            "registration_date": self.__registration_date.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Создает объект User из словаря"""
        user = cls(
            user_id=data["user_id"],
            username=data["username"],
            password="temp",  # Временный пароль
            salt=data["salt"],
            registration_date=datetime.datetime.fromisoformat(data["registration_date"])
        )
        user.__hashed_password = data["hashed_password"]
        return user


class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0):
        self.currency_code = currency_code
        self._balance = balance
    
    @property
    def currency_code(self) -> str:
        return self.__currency_code
    
    @currency_code.setter
    def currency_code(self, value: str):
        if not value or not isinstance(value, str):
            raise ValueError("Код валюты должен быть непустой строкой")
        self.__currency_code = value.upper().strip()
    
    @property
    def balance(self) -> float:
        return self._balance
    
    @balance.setter
    def balance(self, value: float):
        if not isinstance(value, (int, float)):
            raise ValueError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)
    
    def deposit(self, amount: float):
        """Пополнение баланса"""
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительным числом")
        
        self.balance += amount
    
    def withdraw(self, amount: float) -> bool:
        """Снятие средств с кошелька"""
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Сумма снятия должна быть положительным числом")
        
        if amount > self.balance:
            raise InsufficientFundsError(
                available=self.balance,
                required=amount,
                code=self.currency_code
            )  
        
        self.balance -= amount
        return True
    
    def get_balance_info(self) -> dict:
        """Возвращает информацию о балансе"""
        return {
            "currency_code": self.currency_code,
            "balance": self.balance
        }
    
    def to_dict(self) -> dict:
        """Преобразует объект в словарь для сохранения в JSON"""
        return {
            "currency_code": self.currency_code,
            "balance": self.balance
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Создает объект Wallet из словаря"""
        return cls(
            currency_code=data["currency_code"],
            balance=data["balance"]
        )


class Portfolio:
    def __init__(self, user_id: int, wallets: Dict[str, Wallet] = None):
        self.__user_id = user_id
        self.__wallets = wallets or {}
    
    @property
    def user_id(self) -> int:
        return self.__user_id
    
    @property
    def wallets(self) -> Dict[str, Wallet]:
        return self.__wallets.copy()
    
    def add_currency(self, currency_code: str) -> Wallet:
        """Добавляет новый кошелёк в портфель"""
        currency_code = currency_code.upper()
        
        if currency_code in self.__wallets:
            raise ValueError(f"Кошелек для валюты {currency_code} уже существует")
        
        wallet = Wallet(currency_code, 0.0)
        self.__wallets[currency_code] = wallet
        return wallet
    
    def get_wallet(self, currency_code: str) -> Optional[Wallet]:
        """Возвращает объект Wallet по коду валюты"""
        return self.__wallets.get(currency_code.upper())
    
    def get_total_value(self, base_currency: str = 'USD', exchange_rates: Dict[str, float] = None) -> float:
        """Возвращает общую стоимость всех валют в указанной базовой валюте"""
        if not exchange_rates:
            exchange_rates = {}
        
        total_value = 0.0
        
        for currency, wallet in self.__wallets.items():
            if currency == base_currency:
                total_value += wallet.balance
            else:
                rate_key = f"{currency}_{base_currency}"
                if rate_key in exchange_rates:
                    total_value += wallet.balance * exchange_rates[rate_key]
                else:
                    # Если курс не найден, пропускаем эту валюту
                    continue
        
        return total_value
    
    def to_dict(self) -> dict:
        """Преобразует объект в словарь для сохранения в JSON"""
        return {
            "user_id": self.user_id,
            "wallets": {
                currency: wallet.to_dict() 
                for currency, wallet in self.__wallets.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Создает объект Portfolio из словаря"""
        wallets = {}
        for currency, wallet_data in data.get("wallets", {}).items():
            wallets[currency] = Wallet.from_dict(wallet_data)
        
        return cls(
            user_id=data["user_id"],
            wallets=wallets
        )
