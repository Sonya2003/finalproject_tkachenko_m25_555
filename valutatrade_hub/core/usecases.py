import os
import datetime
from typing import Dict, Optional, Any, List

from .models import User, Portfolio, Wallet
from .utils import load_json_data, save_json_data, get_next_id, validate_currency_code, validate_amount
from .currencies import get_currency, CurrencyNotFoundError
from .exceptions import InsufficientFundsError, ApiRequestError

from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.settings import settings
from valutatrade_hub.infra.database import db

class UserManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.users_file = "users.json"
        self._load_users()
    
    def _load_users(self):
        """Загружает пользователей из файла"""
        self.users = {}
        users_data = db.read_data(self.users_file)
        
        for user_data in users_data:
            user = User.from_dict(user_data)
            self.users[user.user_id] = user
    
    def _save_users(self):
        """Сохраняет пользователей в файл"""
        users_data = [user.to_dict() for user in self.users.values()]
        save_json_data(self.users_file, users_data)
    
    def register_user(self, username: str, password: str) -> User:
        """Регистрирует нового пользователя"""
        # Проверяем уникальность имени
        for user in self.users.values():
            if user.username == username:
                raise ValueError("Пользователь с таким именем уже существует")
        
        if len(password) < 4:
            raise ValueError("Пароль должен содержать не менее 4 символов")
        
        user_id = db.get_next_id(self.users_file, "user_id")
        user = User(user_id, username, password)
        self.users[user_id] = user
        self._save_users()
        return user
    
    def authenticate_user(self, username: str, password: str) -> User:
        """Аутентифицирует пользователя"""
        for user in self.users.values():
            if user.username == username:
                if user.verify_password(password):
                    return user
                else:
                    raise ValueError("Неверный пароль")
        raise ValueError("Пользователь не найден")
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Возвращает пользователя по ID"""
        return self.users.get(user_id)


class PortfolioManager:
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or settings.get('data_dir', 'data')
        self.portfolios_file = os.path.join(data_dir, "portfolios.json")
        self._load_portfolios()
    
    def _load_portfolios(self):
        """Загружает портфели из файла"""
        self.portfolios = {}
        portfolios_data = load_json_data(self.portfolios_file)
        
        for portfolio_data in portfolios_data:
            portfolio = Portfolio.from_dict(portfolio_data)
            self.portfolios[portfolio.user_id] = portfolio
    
    def _save_portfolios(self):
        """Сохраняет портфели в файл"""
        portfolios_data = [portfolio.to_dict() for portfolio in self.portfolios.values()]
        save_json_data(self.portfolios_file, portfolios_data)
    
    def get_user_portfolio(self, user_id: int) -> Portfolio:
        """Возвращает портфель пользователя"""
        if user_id not in self.portfolios:
            # Создаем новый портфель, если не существует
            self.portfolios[user_id] = Portfolio(user_id)
            self._save_portfolios()
        
        return self.portfolios[user_id]
    
    def add_currency_to_portfolio(self, user_id: int, currency_code: str) -> Wallet:
        """Добавляет валюту в портфель пользователя"""
        portfolio = self.get_user_portfolio(user_id)
        wallet = portfolio.add_currency(currency_code)
        self._save_portfolios()
        return wallet
    
    def deposit_to_wallet(self, user_id: int, currency_code: str, amount: float):
        """Пополняет кошелек пользователя"""
        portfolio = self.get_user_portfolio(user_id)
        wallet = portfolio.get_wallet(currency_code)
        
        if not wallet:
            wallet = self.add_currency_to_portfolio(user_id, currency_code)
        
        wallet.deposit(amount)
        self._save_portfolios()
    
    def withdraw_from_wallet(self, user_id: int, currency_code: str, amount: float) -> bool:
        """Снимает средства с кошелька пользователя"""
        portfolio = self.get_user_portfolio(user_id)
        wallet = portfolio.get_wallet(currency_code)
        
        if not wallet:
            return False
        
        success = wallet.withdraw(amount)
        
        if success:
            self._save_portfolios()
        
        return success
    
    def get_wallet_balance(self, user_id: int, currency_code: str) -> float:
        """Возвращает баланс кошелька пользователя"""
        portfolio = self.get_user_portfolio(user_id)
        wallet = portfolio.get_wallet(currency_code)
        
        if wallet:
            return wallet.balance
        return 0.0
    
    def get_all_wallets_info(self, user_id: int) -> Dict[str, float]:
        """Возвращает информацию о всех кошельках пользователя"""
        portfolio = self.get_user_portfolio(user_id)
        return {currency: wallet.balance for currency, wallet in portfolio.wallets.items()}

    @log_action("BUY", verbose=True)
    def buy_currency(self, user_id: int, currency_code: str, amount: float) -> Dict[str, Any]:
        try:
            currency = get_currency(currency_code)
        except CurrencyNotFoundError as e:
            raise e
        if not validate_amount(amount):
            raise ValueError("'amount' должен быть положительным числом")
        rate_data = self.exchange_service.get_rate('USD', currency_code)
        if not rate_data:
            raise ApiRequestError(f"не удалось получить курс для USD-{currency_code}")
        
        rate = rate_data['rate']
        cost_usd = amount * (1/rate) if rate != 0 else 0
        portfolio = self.get_user_portfolio(user_id)
        wallet = portfolio.get_wallet(currency_code)
        
        if wallet:
            old_balance = wallet.balance
            self.deposit_to_wallet(user_id, currency_code, amount)
            new_balance = wallet.balance
        else:
            old_balance = 0.0
            self.deposit_to_wallet(user_id, currency_code, amount)
            new_balance = amount
        return {
            "currency": currency_code,
            "amount": amount,
            "rate": rate,
            "cost_usd": cost_usd,
            "old_balance": old_balance,
            "new_balance": new_balance
        }
        
    @log_action("SELL", verbose=True)
    def sell_currency(self, user_id: int, currency_code: str, amount: float) -> Dict[str, Any]:
        """Продажа валюты с валидацией и логированием"""
        try:
            currency = get_currency(currency_code)
        except CurrencyNotFoundError as e:
            raise e
        if not validate_amount(amount):
            raise ValueError("'amount' должен быть положительным числом")
        portfolio = self.get_user_portfolio(user_id)
        wallet = portfolio.get_wallet(currency_code)
        
        if not wallet:
            raise CurrencyNotFoundError(f"У вас нет кошелька '{currency_code}'")
        
        if wallet.balance < amount:
            raise InsufficientFundsError(
                available=wallet.balance,
                required=amount,
                code=currency_code
            )
        rate_data = self.exchange_service.get_rate(currency_code, 'USD')
        if not rate_data:
            raise ApiRequestError(f"не удалось получить курс для {currency_code}-USD")
        
        rate = rate_data['rate']
        revenue_usd = amount * rate
        old_balance = wallet.balance
        success = self.withdraw_from_wallet(user_id, currency_code, amount)
        
        if not success:
            raise Exception("Ошибка при выполнении операции продажи")
        
        new_balance = wallet.balance
        
        return {
            "currency": currency_code,
            "amount": amount,
            "rate": rate,
            "revenue_usd": revenue_usd,
            "old_balance": old_balance,
            "new_balance": new_balance
        }
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or settings.get('data_dir', 'data')
        self.portfolios_file = os.path.join(self.data_dir, "portfolios.json")
        self.exchange_service = ExchangeRateService(self.data_dir)
        self._load_portfolios()

class ExchangeRateService:
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or settings.get('data_dir', 'data')
        self.rates_file = os.path.join(self.data_dir, "rates.json")
        self.rates_ttl = settings.get('rates_ttl_seconds', 300)
        self._load_rates()
    
    def _load_rates(self):
        """Загружает курсы из файла"""
        rates_data = load_json_data(self.rates_file)
        if isinstance(rates_data, list):
            
            self.rates = {}
            for item in rates_data:
                if isinstance(item, dict):
                    self.rates.update(item)
        elif isinstance(rates_data, dict):
            self.rates = rates_data
        else:
            self.rates = {}
    
    def _save_rates(self):
        """Сохраняет курсы в файл"""
        save_json_data(self.rates_file, self.rates)
    
    def get_rate(self, from_currency: str, to_currency: str) -> Optional[Dict[str, Any]]:
        """Получает курс между двумя валютами"""
        try:
           get_currency(from_currency)
           get_currency(to_currency)
        except CurrencyNotFoundError as e:
           raise e
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        if from_currency == to_currency:
            return {
                "rate": 1.0,
                "updated_at": datetime.datetime.now().isoformat()
            }
        
        rate_key = f"{from_currency}_{to_currency}"
        
        if rate_key in self.rates:
            rate_data = self.rates[rate_key]
            
            if "updated_at" in rate_data:
                try:
                    updated_at = datetime.datetime.fromisoformat(rate_data["updated_at"])
                    if (datetime.datetime.now() - updated_at).total_seconds() < self.rates_ttl:
                        return rate_data
                except (ValueError, TypeError):
                    pass
        
        return self._update_rate(from_currency, to_currency)
    
    def _get_stub_rate(self, from_currency: str, to_currency: str) -> Optional[Dict[str, Any]]:
        """Обновляет курс валюты (заглушка с имитацией API)"""
        try:
            rate_data = self._get_stub_rate(from_currency, to_currency)
            if rate_data:
                rate_key = f"{from_currency}_{to_currency}"
                self.rates[rate_key] = rate_data
                self._save_rates()
                return rate_data
            else:
                raise ApiRequestError("курс не найден в заглушке")
        except Exception as e:
            raise ApiRequestError(str(e))
    def _get_stub_rate(self, from_currency: str, to_currency: str) -> Optional[Dict[str, Any]]:
            stub_rates = {
                "USD_EUR": {"rate": 0.85, "updated_at": datetime.datetime.now().isoformat()},
                "EUR_USD": {"rate": 1.18, "updated_at": datetime.datetime.now().isoformat()},
                "USD_BTC": {"rate": 0.00001685, "updated_at": datetime.datetime.now().isoformat()},
                "BTC_USD": {"rate": 59337.21, "updated_at": datetime.datetime.now().isoformat()},
                "USD_ETH": {"rate": 0.000269, "updated_at": datetime.datetime.now().isoformat()},
                "ETH_USD": {"rate": 3720.00, "updated_at": datetime.datetime.now().isoformat()},
                "USD_RUB": {"rate": 98.42, "updated_at": datetime.datetime.now().isoformat()},
                "RUB_USD": {"rate": 0.01016, "updated_at": datetime.datetime.now().isoformat()},
                "EUR_BTC": {"rate": 0.0000142, "updated_at": datetime.datetime.now().isoformat()},
                "BTC_EUR": {"rate": 70500.00, "updated_at": datetime.datetime.now().isoformat()},
            }
        
            rate_key = f"{from_currency}_{to_currency}"
            if rate_key in stub_rates:
                return stub_rates[rate_key]
            return None
       
    
    def get_all_rates(self) -> Dict[str, float]:
        """Возвращает все доступные курсы в упрощенном формате"""
        rates_dict = {}
        for rate_key, rate_data in self.rates.items():
            if isinstance(rate_data, dict) and "rate" in rate_data:
                rates_dict[rate_key] = rate_data["rate"]
        return rates_dict
    
    def update_rate(self, from_currency: str, to_currency: str, rate: float):
        """Обновляет курс валюты"""
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        rate_key = f"{from_currency}_{to_currency}"
        self.rates[rate_key] = {
            "rate": rate,
            "updated_at": datetime.datetime.now().isoformat()
        }
        self._save_rates()
