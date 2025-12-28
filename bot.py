"""
Главный файл бота - точка входа
"""
import logging
from telegram.ext import Application

from config import TELEGRAM_BOT_TOKEN
from utils import setup_logger
from handlers import get_all_handlers
from tasks import start_scheduler

# Настройка логирования
logger = setup_logger()


def main():
    """Запуск бота"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден в .env!")
        return
    
    # Создаём приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем все обработчики
    for handler in get_all_handlers():
        application.add_handler(handler)
    
    # Запускаем планировщик задач
    start_scheduler(application.bot)
    
    logger.info("=" * 60)
    logger.info("🤖 БОТ ЗАПУЩЕН!")
    logger.info("=" * 60)
    logger.info("✅ Модули загружены:")
    logger.info("  📝 Верификация и авторизация")
    logger.info("  🏛️ Политика и партии")
    logger.info("  🗳️ Голосования и выборы")
    logger.info("  ⚙️ Админ-панель")
    logger.info("  📊 Планировщик задач")
    logger.info("")
    logger.info("Нажми Ctrl+C для остановки")
    logger.info("=" * 60)
    
    # Запуск бота
    application.run_polling(allowed_updates=['message', 'callback_query'])


if __name__ == '__main__':
    main()
