import argparse
from typing import Optional
from ..core.utils import format_currency_amount
from ..core.exceptions import InsufficientFundsError, CurrencyNotFoundError, ApiRequestError
from ..core.currencies import get_currency, get_all_currencies
from valutatrade_hub.core import UserManager, PortfolioManager, ExchangeRateService
from ..parser_service import RatesUpdater


class CLIInterface:
    def __init__(self):
        self.user_manager = UserManager()
        self.portfolio_manager = PortfolioManager()
        self.exchange_service = ExchangeRateService()
        self.parser_updater = RatesUpdater()
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
        print("\n" + "=" * 40)
        print("ГЛАВНОЕ МЕНЮ")
        print("=" * 40)
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
        print("\n" + "=" * 40)
        print(f"Панель управления: {self.current_user.username}")
        print("=" * 40)
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
            print(f"Пользователь '{
                  username}' зарегистрирован (id={user.user_id})")
            print("Теперь вы можете войти в систему.")
        except ValueError as e:
            print(f"Ошибка: {e}")

    def _interactive_login(self):
        """Интерактивный вход"""
        print("\n--- Вход ---")
        username = input("Имя пользователя: ").strip()
        password = input("Пароль: ").strip()

        try:
            self.current_user = self.user_manager.authenticate_user(
                username, password)
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
            print(f"Пользователь '{username}' зарегистрирован (id={
                  user.user_id}). Войдите: login --username {username} --password [ваш_пароль]")
        except ValueError as e:
            print(f"Ошибка: {e}")

    def login(self, args):
        """Команда login"""
        username = args.username
        password = args.password

        try:
            self.current_user = self.user_manager.authenticate_user(
                username, password)
            print(f"Вы вошли как '{username}'")
        except ValueError as e:
            print(f"Ошибка: {e}")

    def show_portfolio(self, args):
        """Команда show-portfolio"""
        if not self.current_user:
            print("Ошибка: Сначала выполните login")
            return

        base_currency = args.base.upper() if args.base else 'USD'

        portfolio = self.portfolio_manager.get_user_portfolio(
            self.current_user.user_id)
        exchange_rates = self.exchange_service.get_all_rates()

        print(f"Портфель пользователя '{
              self.current_user.username}' (база: {base_currency}):")

        if not portfolio.wallets:
            print("  У вас пока нет кошельков")
            return

        total_value = 0.0

        for currency, wallet in portfolio.wallets.items():
            balance = wallet.balance
            if currency == base_currency:
                value = balance
                print(f"  - {currency}: {format_currency_amount(balance, currency)
                                         } → {format_currency_amount(value, base_currency)} {base_currency}")
            else:
                rate_key = f"{currency}_{base_currency}"
                if rate_key in exchange_rates:
                    rate = exchange_rates[rate_key]
                    value = balance * rate
                    print(f"  - {currency}: {format_currency_amount(balance, currency)} → {
                          format_currency_amount(value, base_currency)} {base_currency} (курс: {rate:.6f})")
                    total_value += value
                else:
                    print(
                        f"  - {currency}: {format_currency_amount(balance, currency)} → курс недоступен")

            if currency == base_currency:
                total_value += value

        print(f"\nИТОГО: {format_currency_amount(
            total_value, base_currency)} {base_currency}")

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

            print(f"Покупка выполнена: {format_currency_amount(amount, currency)} {
                  currency} по курсу {result['rate']:.6f} USD/{currency}")
            print("Изменения в портфеле:")
            print(f"  - {currency}: было {format_currency_amount(result['old_balance'], currency)} → стало {
                  format_currency_amount(result['new_balance'], currency)}")
            print(f"Оценочная стоимость покупки: {
                  format_currency_amount(result['cost_usd'], 'USD')} USD")

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
            print(f"Продажа выполнена: {format_currency_amount(amount, currency)} {
                  currency} по курсу {result['rate']:.2f} {currency}/USD")
            print("Изменения в портфеле:")
            print(f"  - {currency}: было {format_currency_amount(result['old_balance'], currency)} → стало {
                  format_currency_amount(result['new_balance'], currency)}")
            print(f"Оценочная выручка: {format_currency_amount(
                result['revenue_usd'], 'USD')} USD")
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
            rate_data = self.exchange_service.get_rate(
                from_currency, to_currency)
            if not rate_data:
                raise ApiRequestError("курс недоступен")
            rate = rate_data['rate']
            updated_at = rate_data['updated_at']
            from datetime import datetime
            updated_time = datetime.fromisoformat(
                updated_at).strftime("%Y-%m-%d %H:%M:%S")
            print(f"Курс {from_currency}={to_currency}: {
                  rate:.8f} (обновлено: {updated_time})")
            print("Информация о валютах:")
            print(f"  - {from_curr_obj.get_display_info()}")
            print(f"  - {to_curr_obj.get_display_info()}")
            reverse_rate_data = self.exchange_service.get_rate(
                to_currency, from_currency)
            if reverse_rate_data:
                reverse_rate = reverse_rate_data['rate']
                print(f"Обратный курс {to_currency}={
                      from_currency}: {reverse_rate:.8f}")
        except CurrencyNotFoundError as e:
            print(f"Ошибка: {e}")
            self._show_currency_help()
        except ApiRequestError as e:
            print(f"Ошибка: {e}")
            print("Повторите попытку позже или проверьте подключение к сети")

    def run(self):
        """Запускает CLI интерфейс"""
        parser = argparse.ArgumentParser(
            description='ValutaTrade Hub - Trading Platform')
        subparsers = parser.add_subparsers(
            dest='command', help='Доступные команды')

        # register command
        register_parser = subparsers.add_parser(
            'register', help='Регистрация нового пользователя')
        register_parser.add_argument(
            '--username', required=True, help='Имя пользователя')
        register_parser.add_argument(
            '--password', required=True, help='Пароль')

        # login command
        login_parser = subparsers.add_parser('login', help='Вход в систему')
        login_parser.add_argument(
            '--username', required=True, help='Имя пользователя')
        login_parser.add_argument('--password', required=True, help='Пароль')

        # show-portfolio command
        portfolio_parser = subparsers.add_parser(
            'show-portfolio', help='Показать портфель')
        portfolio_parser.add_argument(
            '--base', help='Базовая валюта (по умолчанию: USD)')

        # buy command
        buy_parser = subparsers.add_parser('buy', help='Купить валюту')
        buy_parser.add_argument(
            '--currency', required=True, help='Код покупаемой валюты')
        buy_parser.add_argument(
            '--amount', type=float, required=True, help='Количество покупаемой валюты')

        # sell command
        sell_parser = subparsers.add_parser('sell', help='Продать валюту')
        sell_parser.add_argument(
            '--currency', required=True, help='Код продаваемой валюты')
        sell_parser.add_argument(
            '--amount', type=float, required=True, help='Количество продаваемой валюты')

        # get-rate command
        rate_parser = subparsers.add_parser(
            'get-rate', help='Получить курс валют')
        rate_parser.add_argument(
            '--from', dest='fr', required=True, help='Исходная валюта')
        rate_parser.add_argument('--to', required=True, help='Целевая валюта')

        # Parser Service commands
        update_parser = subparsers.add_parser(
            'update-rates', help='Update currency rates from APIs')
        update_parser.add_argument('--source', choices=['coingecko', 'exchangerate'],
                                   help='Update from specific source')
        show_rates_parser = subparsers.add_parser(
            'show-rates', help='Show current exchange rates')
        show_rates_parser.add_argument(
            '--currency', help='Filter by currency code')
        show_rates_parser.add_argument(
            '--top', type=int, help='Show top N currencies by value')
        _start_parser = subparsers.add_parser(
            'start-parser', help='Start automatic rates updates')
        _stop_parser = subparsers.add_parser(
            'stop-parser', help='Stop automatic rates updates')

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
            elif args.command == 'update-rates':
                self.update_rates(args)
            elif args.command == 'show-rates':
                self.show_rates(args)
            elif args.command == 'start-parser':
                self.start_parser_scheduler(args)
            elif args.command == 'stop-parser':
                self.stop_parser_scheduler(args)
        except Exception as e:
            print(f"Произошла ошибка: {e}")

    def update_rates(self, args):
        """Команда update-rates - обновление курсов валют"""
        sources = None
        if args.source:
            sources = [args.source.lower()]
            valid_sources = ['coingecko', 'exchangerate']
            if sources[0] not in valid_sources:
                print(f"Error: Unknown source '{args.source}'. Use: {
                      ', '.join(valid_sources)}")
                return

        print("Starting rates update...")

        try:
            result = self.parser_updater.run_update(sources)

            if result['success']:
                print("Update successful!")
                print(f"   Sources processed: {
                      ', '.join(result['sources_processed'])}")
                print(f"   Total rates: {result['total_rates']}")
                print(f"   Cache updated: {result['updated_rates']} rates")
                print(f"   History saved: {
                      result['historical_records']} records")
                print(f"   Last refresh: {result['updated_at']}")
            else:
                print(" Update completed with errors:")
                for error in result['errors']:
                    print(f"   - {error}")
                print("   Check logs for details.")

        except Exception as e:
            print(f"Critical error during update: {e}")

    def show_rates(self, args):
        """Команда show-rates - просмотр текущих курсов"""
        try:
            rates_data = self.parser_updater.storage.load_current_rates()

            if not rates_data:
                print("Local cache is empty. Run 'update-rates' to load data.")
                return

            # Применяем фильтры
            filtered_rates = self._filter_rates(rates_data, args)

            if not filtered_rates:
                currency_msg = f" for currency '{
                    args.currency}'" if args.currency else ""
                print(f"No rates found{currency_msg}.")
                return

            # Получаем статус обновления
            status = self.parser_updater.get_update_status()

            print(f"Rates from cache (Status: {status['status'].upper()})")
            if status['status'] == 'outdated':
                print("    Rates may be outdated. Consider running 'update-rates'")
            print(f"   Total rates: {len(filtered_rates)}")
            print(f"   Sources: {', '.join(status['sources'])}")
            print()

            # Сортируем и выводим
            sorted_rates = sorted(filtered_rates.items())
            for rate_key, rate_info in sorted_rates:
                currency_from, currency_to = rate_key.split('_')
                rate_value = rate_info['rate']
                source = rate_info.get('source', 'unknown')
                _updated = rate_info.get('updated_at', 'unknown')

                print(f"   {currency_from:4} → {currency_to:3}: {
                      rate_value:12.6f}  (source: {source:12})")

        except Exception as e:
            print(f"Error reading rates: {e}")

    def _filter_rates(self, rates_data: dict, args) -> dict:
        """Фильтрует курсы по аргументам командной строки"""
        filtered = {}

        for rate_key, rate_info in rates_data.items():
            # Фильтр по валюте
            if args.currency:
                currency_filter = args.currency.upper()
                if currency_filter not in rate_key:
                    continue

            filtered[rate_key] = rate_info

        # Фильтр по top N
        if args.top and args.top > 0:
            # Сортируем по значению курса (по убыванию)
            sorted_rates = sorted(
                filtered.items(),
                key=lambda x: x[1]['rate'],
                reverse=True
            )
            filtered = dict(sorted_rates[:args.top])

        return filtered

    def start_parser_scheduler(self, args):
        """Запускает планировщик парсера"""
        print("Starting parser scheduler...")
        try:
            self.parser_scheduler.start_scheduler()
            interval = self.parser_scheduler.config.UPDATE_INTERVAL
            print(
                f"Parser scheduler started (update every {interval} minutes)")
            print("Use 'stop-parser' to stop the scheduler")
        except Exception as e:
            print(f"Failed to start scheduler: {e}")

    def stop_parser_scheduler(self, args):
        """Останавливает планировщик парсера"""
        print("Stopping parser scheduler...")
        try:
            self.parser_scheduler.stop_scheduler()
            print("Parser scheduler stopped")
        except Exception as e:
            print(f"Failed to stop scheduler: {e}")
