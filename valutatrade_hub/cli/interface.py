import argparse
import sys
import os
import getpass
from typing import Optional
from ..core.exceptions import InsufficientFundsError, CurrencyNotFoundError, ApiRequestError
from ..core.currencies import get_currency, get_all_currencies
class CLIInterface:
    def __init__(self):
        self.user_manager = UserManager()
        self.portfolio_manager = PortfolioManager()
        self.exchange_service = ExchangeRateService()
        self.current_user: Optional[object] = None
    def interactive_mode(self):
        """Интерактивный режим с сохранением сессии"""
        print("=== Добро пожаловать в ValutaTrade Hub! ===")
    
        while True:
            if not self.current_user:
                self._interactive_main_menu()
            else:
                self._interactive_user_menu()

    def _interactive_main_menu(self):
        """Главное меню в интерактивном режиме"""
        print("\n" + "="*40)
        print("ГЛАВНОЕ МЕНЮ")
        print("="*40)
        print("1. Регистрация")
        print("2. Вход в систему")
        print("3. Выход")
    
        choice = input("\nВыберите действие (1-3): ").strip()
    
        if choice == "1":
            self._interactive_register()
        elif choice == "2":
            self._interactive_login()
        elif choice == "3":
            print("До свидания!")
            exit()
        else:
            print("Неверный выбор")

    def _interactive_user_menu(self):
        """Меню пользователя в интерактивном режиме"""
        print(f"\n" + "="*40)
        print(f"Панель управления: {self.current_user.username}")
        print("="*40)
        print("1. Показать портфель")
        print("2. Купить валюту")
        print("3. Продать валюту")
        print("4. Получить курс")
        print("5. Выход из аккаунта")
    
        choice = input("\nВыберите действие (1-5): ").strip()
    
        if choice == "1":
            self._interactive_show_portfolio()
        elif choice == "2":
            self._interactive_buy()
        elif choice == "3":
            self._interactive_sell()
        elif choice == "4":
            self._interactive_get_rate()
        elif choice == "5":
            self.current_user = None
            print("Выход из аккаунта выполнен")
        else:
            print("Неверный выбор")

    def _interactive_register(self):
        """Интерактивная регистрация"""
        print("\n--- Регистрация ---")
        username = input("Имя пользователя: ").strip()
        password = input("Пароль: ").strip()
    
        try:
            user = self.user_manager.register_user(username, password)
            print(f"Пользователь '{username}' зарегистрирован (id={user.user_id})")
            print("Теперь вы можете войти в систему.")
        except ValueError as e:
            print(f"Ошибка: {e}")

    def _interactive_login(self):
        """Интерактивный вход"""
        print("\n--- Вход ---")
        username = input("Имя пользователя: ").strip()
        password = input("Пароль: ").strip()
    
        try:
            self.current_user = self.user_manager.authenticate_user(username, password)
            print(f"Вы вошли как '{username}'")
        except ValueError as e:
            print(f"Ошибка: {e}")

    def _interactive_show_portfolio(self):
        """Интерактивный показ портфеля"""
        base_currency = input("Базовая валюта (по умолчанию USD): ").strip()
        if not base_currency:
            base_currency = 'USD'
    
  
        class Args:
            def __init__(self, base):
                self.base = base
    
        self.show_portfolio(Args(base_currency))

    def _interactive_buy(self):
        """Интерактивная покупка"""
        print("\n--- Покупка валюты ---")
        currency = input("Код валюты (например, BTC): ").strip().upper()
        amount_str = input("Количество: ").strip()
    
        try:
            amount = float(amount_str)
      
            class Args:
                def __init__(self, currency, amount):
                    self.currency = currency
                    self.amount = amount
        
            self.buy(Args(currency, amount))
        except ValueError:
            print("Ошибка: количество должно быть числом")

    def _interactive_sell(self):
        """Интерактивная продажа"""
        print("\n--- Продажа валюты ---")
        currency = input("Код валюты: ").strip().upper()
        amount_str = input("Количество: ").strip()
    
        try:
            amount = float(amount_str)
       
            class Args:
                def __init__(self, currency, amount):
                    self.currency = currency
                    self.amount = amount
        
            self.sell(Args(currency, amount))
        except ValueError:
            print("Ошибка: количество должно быть числом")

    def _interactive_get_rate(self):
        """Интерактивный получение курса"""
        print("\n--- Получение курса ---")
        from_curr = input("Исходная валюта: ").strip().upper()
        to_curr = input("Целевая валюта: ").strip().upper()
    

        class Args:
            def __init__(self, fr, to):
                self.fr = fr
                self.to = to
    
        self.get_rate(Args(from_curr, to_curr))
    
    def register(self, args):
        """Команда register"""
        username = args.username
        password = args.password
        
        try:
            user = self.user_manager.register_user(username, password)
            # Создаем пустой портфель для нового пользователя
            self.portfolio_manager.get_user_portfolio(user.user_id)
            print(f"Пользователь '{username}' зарегистрирован (id={user.user_id}). Войдите: login --username {username} --password [ваш_пароль]")
        except ValueError as e:
            print(f"Ошибка: {e}")
    
    def login(self, args):
        """Команда login"""
        username = args.username
        password = args.password
        
        try:
            self.current_user = self.user_manager.authenticate_user(username, password)
            print(f"Вы вошли как '{username}'")
        except ValueError as e:
            print(f"Ошибка: {e}")
    
    def show_portfolio(self, args):
        """Команда show-portfolio"""
        if not self.current_user:
            print("Ошибка: Сначала выполните login")
            return
        
        base_currency = args.base.upper() if args.base else 'USD'
        
        portfolio = self.portfolio_manager.get_user_portfolio(self.current_user.user_id)
        exchange_rates = self.exchange_service.get_all_rates()
        
        print(f"Портфель пользователя '{self.current_user.username}' (база: {base_currency}):")
        
        if not portfolio.wallets:
            print("  У вас пока нет кошельков")
            return
        
        total_value = 0.0
        
        for currency, wallet in portfolio.wallets.items():
            balance = wallet.balance
            if currency == base_currency:
                value = balance
                print(f"  - {currency}: {format_currency_amount(balance, currency)} → {format_currency_amount(value, base_currency)} {base_currency}")
            else:
                rate_key = f"{currency}_{base_currency}"
                if rate_key in exchange_rates:
                    rate = exchange_rates[rate_key]
                    value = balance * rate
                    print(f"  - {currency}: {format_currency_amount(balance, currency)} → {format_currency_amount(value, base_currency)} {base_currency} (курс: {rate:.6f})")
                    total_value += value
                else:
                    print(f"  - {currency}: {format_currency_amount(balance, currency)} → курс недоступен")
            
            if currency == base_currency:
                total_value += value
        
        print(f"\nИТОГО: {format_currency_amount(total_value, base_currency)} {base_currency}")
    
    def buy(self, args):
        """Команда buy"""
        if not self.current_user:
            print("Ошибка: Сначала выполните login")
            return
        
        currency = args.currency.upper()
        amount = args.amount
        
        try:
            result = self.portfolio_manager.buy_currency(
                self.current_user.user_id, currency, amount
            )
        
            print(f"Покупка выполнена: {format_currency_amount(amount, currency)} {currency} по курсу {result['rate']:.6f} USD/{currency}")
            print(f"Изменения в портфеле:")
            print(f"  - {currency}: было {format_currency_amount(result['old_balance'], currency)} → стало {format_currency_amount(result['new_balance'], currency)}")
            print(f"Оценочная стоимость покупки: {format_currency_amount(result['cost_usd'], 'USD')} USD")
        
        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}")
            self._show_currency_help()
        except InsufficientFundsError as e:
            print(f"Ошибка: {e}")
        except ApiRequestError as e:
            print(f"Ошибка: {e}")
            print("Повторите попытку позже или проверьте подключение к сети")
        except ValueError as e:
            print(f"Ошибка: {e}")
    
    def sell(self, args):
        """Команда sell"""
        if not self.current_user:
            print("Ошибка: Сначала выполните login")
            return
        
        currency = args.currency.upper()
        amount = args.amount
        
        try:
            result = self.portfolio_manager.sell_currency(
                self.current_user.user_id, currency, amount
            )
            print(f"Продажа выполнена: {format_currency_amount(amount, currency)} {currency} по курсу {result['rate']:.2f} {currency}/USD")
            print(f"Изменения в портфеле:")
            print(f"  - {currency}: было {format_currency_amount(result['old_balance'], currency)} → стало {format_currency_amount(result['new_balance'], currency)}")
            print(f"Оценочная выручка: {format_currency_amount(result['revenue_usd'], 'USD')} USD")
        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}")
            self._show_currency_help()
        except InsufficientFundsError as e:
            print(f"Ошибка: {e}")
        except ApiRequestError as e:
            print(f"Ошибка: {e}")
            print("Повторите попытку позже или проверьте подключение к сети")
        except ValueError as e:
            print(f"Ошибка: {e}")
    def _show_currency_help(self):
        """Показывает справку по доступным валютам"""
        print("\nДоступные валюты:")
        currencies = get_all_currencies()
        for code, currency in currencies.items():
            print(f"  - {code}: {currency.name}")
        print("Используйте 'get-rate --from USD --to CODE' для проверки курса")

    def get_rate(self, args):
        """Команда get-rate"""
        from_currency = args.fr.upper()
        to_currency = args.to.upper()
        
        try:
            from_curr_obj = get_currency(from_currency)
            to_curr_obj = get_currency(to_currency)
            rate_data = self.exchange_service.get_rate(from_currency, to_currency)
            if not rate_data:
               raise ApiRequestError("курс недоступен")
            rate = rate_data['rate']
            updated_at = rate_data['updated_at']
            from datetime import datetime
            updated_time = datetime.fromisoformat(updated_at).strftime("%Y-%m-%d %H:%M:%S")
            print(f"Курс {from_currency}={to_currency}: {rate:.8f} (обновлено: {updated_time})")
            print(f"Информация о валютах:")
            print(f"  - {from_curr_obj.get_display_info()}")
            print(f"  - {to_curr_obj.get_display_info()}")
            reverse_rate_data = self.exchange_service.get_rate(to_currency, from_currency)
            if reverse_rate_data:
               reverse_rate = reverse_rate_data['rate']
               print(f"Обратный курс {to_currency}={from_currency}: {reverse_rate:.8f}")
        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}")
            self._show_currency_help()
        except ApiRequestError as e:
            print(f"Ошибка: {e}")
            print("Повторите попытку позже или проверьте подключение к сети")
 
   
    def run(self):
        """Запускает CLI интерфейс"""
        parser = argparse.ArgumentParser(description='ValutaTrade Hub - Trading Platform')
        subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
        
        # register command
        register_parser = subparsers.add_parser('register', help='Регистрация нового пользователя')
        register_parser.add_argument('--username', required=True, help='Имя пользователя')
        register_parser.add_argument('--password', required=True, help='Пароль')
        
        # login command
        login_parser = subparsers.add_parser('login', help='Вход в систему')
        login_parser.add_argument('--username', required=True, help='Имя пользователя')
        login_parser.add_argument('--password', required=True, help='Пароль')
        
        # show-portfolio command
        portfolio_parser = subparsers.add_parser('show-portfolio', help='Показать портфель')
        portfolio_parser.add_argument('--base', help='Базовая валюта (по умолчанию: USD)')
        
        # buy command
        buy_parser = subparsers.add_parser('buy', help='Купить валюту')
        buy_parser.add_argument('--currency', required=True, help='Код покупаемой валюты')
        buy_parser.add_argument('--amount', type=float, required=True, help='Количество покупаемой валюты')
        
        # sell command
        sell_parser = subparsers.add_parser('sell', help='Продать валюту')
        sell_parser.add_argument('--currency', required=True, help='Код продаваемой валюты')
        sell_parser.add_argument('--amount', type=float, required=True, help='Количество продаваемой валюты')
        
        # get-rate command
        rate_parser = subparsers.add_parser('get-rate', help='Получить курс валют')
        rate_parser.add_argument('--from', dest='fr', required=True, help='Исходная валюта')
        rate_parser.add_argument('--to', required=True, help='Целевая валюта')
        
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            return
        
        # Выполняем команду
        try:
            if args.command == 'register':
                self.register(args)
            elif args.command == 'login':
                self.login(args)
            elif args.command == 'show-portfolio':
                self.show_portfolio(args)
            elif args.command == 'buy':
                self.buy(args)
            elif args.command == 'sell':
                self.sell(args)
            elif args.command == 'get-rate':
                self.get_rate(args)
        except Exception as e:
            print(f"Произошла ошибка: {e}")
