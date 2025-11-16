import threading
import time
import logging
import schedule
from .config import ParserConfig
from .updater import RatesUpdater

logger = logging.getLogger(__name__)


class ParserScheduler:
    """Планировщик периодического обновления курсов"""

    def __init__(self, config: ParserConfig = None):
        self.config = config or ParserConfig()
        self.updater = RatesUpdater(self.config)
        self.scheduler_thread = None
        self.stop_event = threading.Event()

    def scheduled_update(self):
        """Задача для планировщика - обновление курсов"""
        try:
            logger.info("Running scheduled rates update...")
            result = self.updater.run_update()

            if result['success']:
                logger.info(f"Scheduled update completed: {
                            result['total_rates']} rates")
            else:
                logger.warning(f"️Scheduled update completed with errors: {
                               len(result['errors'])}")

        except Exception as e:
            logger.error(f"Scheduled update failed: {e}")

    def start_scheduler(self):
        """Запускает планировщик в отдельном потоке"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            logger.warning("Scheduler is already running")
            return

        # Настраиваем расписание
        schedule.every(self.config.UPDATE_INTERVAL).minutes.do(
            self.scheduled_update)

        def run_scheduler():
            logger.info(f"Starting parser scheduler (interval: {
                        self.config.UPDATE_INTERVAL} minutes)")

            while not self.stop_event.is_set():
                try:
                    schedule.run_pending()
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Scheduler error: {e}")
                    time.sleep(10)  # Пауза при ошибке

        self.stop_event.clear()
        self.scheduler_thread = threading.Thread(
            target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Parser scheduler started successfully")

    def stop_scheduler(self):
        """Останавливает планировщик"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            logger.info("Stopping parser scheduler...")
            self.stop_event.set()
            self.scheduler_thread.join(timeout=5)
            schedule.clear()
            logger.info("Parser scheduler stopped")
        else:
            logger.info("Scheduler is not running")

    def run_once(self):
        """Выполняет однократное обновление"""
        return self.updater.run_update()
