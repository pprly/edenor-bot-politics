"""
Декораторы для проверки прав доступа
"""
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
import logging

from database import db
from utils.auth import auth_checker
from config import ADMIN_IDS

logger = logging.getLogger(__name__)


def require_auth(func):
    """Декоратор для проверки авторизации пользователя"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return
        
        telegram_id = user.id
        
        # Проверяем есть ли в БД
        user_data = db.get_user(telegram_id)
        
        if not user_data:
            # Пытаемся проверить через API
            is_linked, player_data = auth_checker.check_player(telegram_id)
            
            if is_linked:
                minecraft_username = player_data.get('username')
                db.add_user(telegram_id, minecraft_username)
                logger.info(f"✅ Новый пользователь добавлен: {minecraft_username}")
            else:
                # Отправляем сообщение о необходимости регистрации
                from config import REGISTRATION_BOT
                if hasattr(update, 'callback_query') and update.callback_query:
                    await update.callback_query.answer(
                        "⛔ Сначала пройди верификацию /start",
                        show_alert=True
                    )
                else:
                    await update.message.reply_text(
                        f"❌ <b>Аккаунт не привязан к серверу</b>\n\n"
                        f"Для использования бота:\n"
                        f"1️⃣ Привяжи Telegram к игровому аккаунту через {REGISTRATION_BOT}\n"
                        f"2️⃣ После привязки напиши /start",
                        parse_mode='HTML'
                    )
                return
        
        return await func(update, context, *args, **kwargs)
    return wrapper


def require_admin(func):
    """Декоратор для проверки прав администратора"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return
        
        telegram_id = user.id
        
        if telegram_id not in ADMIN_IDS:
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.answer(
                    "⛔ Доступно только администраторам",
                    show_alert=True
                )
            else:
                await update.message.reply_text("⛔ У тебя нет прав администратора")
            logger.warning(f"⚠️ Попытка доступа к админ функции: {telegram_id}")
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper


def require_party_leader(func):
    """Декоратор для проверки что пользователь - глава партии"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return
        
        telegram_id = user.id
        party = db.get_user_party(telegram_id)
        
        if not party:
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.answer(
                    "❌ Ты не состоишь в партии",
                    show_alert=True
                )
            return
        
        if party['leader_telegram_id'] != telegram_id:
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.answer(
                    "❌ Только глава партии может это сделать",
                    show_alert=True
                )
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper


def require_deputy(func):
    """Декоратор для проверки что пользователь - депутат"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return
        
        telegram_id = user.id
        
        if not db.is_deputy(telegram_id):
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.answer(
                    "❌ Только для депутатов",
                    show_alert=True
                )
            else:
                await update.message.reply_text("❌ Это действие доступно только депутатам")
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper
