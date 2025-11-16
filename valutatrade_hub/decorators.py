import functools
import os
import logging
import datetime
from typing import Any, Callable
from .infra.settings import settings


def setup_logging():
    """Настраивает систему логирования"""
    log_file = settings.get('log_file', 'logs/actions.log')
    log_level = settings.get('log_level', 'INFO')

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()  # Также выводим в консоль
        ]
    )


setup_logging()


def log_action(action: str, verbose: bool = False):
    """Декоратор для логирования действий"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger(__name__)

            log_data = {
                'timestamp': datetime.datetime.now().isoformat(),
                'action': action,
                'result': 'OK'
            }

            try:

                if args and hasattr(
                        args[0], 'current_user') and args[0].current_user:
                    log_data['username'] = args[0].current_user.username
                    log_data['user_id'] = args[0].current_user.user_id

                if action in ['BUY', 'SELL'] and len(args) > 1:
                    log_data['currency'] = getattr(args[1], 'currency', None)
                    log_data['amount'] = getattr(args[1], 'amount', None)

                result = func(*args, **kwargs)

                if verbose:
                    log_data['context'] = "Подробный контекст..."

                logger.info(f"{action} {log_data}")
                return result

            except Exception as e:

                log_data['result'] = 'ERROR'
                log_data['error_type'] = type(e).__name__
                log_data['error_message'] = str(e)
                logger.error(f"{action} {log_data}")
                raise

        return wrapper
    return decorator
