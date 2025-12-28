"""
Настройка системы логирования
"""
import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logger():
    """Настроить логирование в файл и консоль"""
    
    # Создаём папку для логов
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Имя файла с текущей датой
    log_file = log_dir / f"bot_{datetime.now().strftime('%Y-%m-%d')}.log"
    
    # Формат логов
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Настройка root logger
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            # Вывод в файл
            logging.FileHandler(log_file, encoding='utf-8'),
            # Вывод в консоль
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Отключаем излишнюю болтливость библиотек
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("🤖 Система логирования запущена")
    logger.info(f"📁 Логи сохраняются в: {log_file}")
    logger.info("=" * 60)
    
    return logger
