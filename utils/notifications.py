"""
Отправка уведомлений пользователям
"""
import logging
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


async def send_notification(bot: Bot, telegram_id: int, message: str, parse_mode: str = 'HTML'):
    """
    Отправить уведомление пользователю
    
    Args:
        bot: Экземпляр бота
        telegram_id: ID пользователя
        message: Текст сообщения
        parse_mode: Режим парсинга (HTML/Markdown)
    """
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode=parse_mode
        )
        logger.info(f"✅ Уведомление отправлено пользователю {telegram_id}")
    except TelegramError as e:
        logger.error(f"❌ Ошибка отправки уведомления {telegram_id}: {e}")


async def notify_party_members(bot: Bot, party_id: int, message: str, exclude_id: int = None):
    """
    Отправить уведомление всем членам партии
    
    Args:
        bot: Экземпляр бота
        party_id: ID партии
        message: Текст сообщения
        exclude_id: ID пользователя которого исключить (опционально)
    """
    from database import db
    
    members = db.get_party_members(party_id)
    
    for member in members:
        if exclude_id and member['telegram_id'] == exclude_id:
            continue
        
        await send_notification(bot, member['telegram_id'], message)


async def notify_admins(bot: Bot, message: str):
    """
    Отправить уведомление всем администраторам
    
    Args:
        bot: Экземпляр бота
        message: Текст сообщения
    """
    from config import ADMIN_IDS
    
    for admin_id in ADMIN_IDS:
        await send_notification(bot, admin_id, message)
