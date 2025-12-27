"""
Декораторы для проверки прав доступа
"""
from telegram import Update
from telegram.ext import ContextTypes

from config import verified_users
from utils.auth_checker import auth_checker


def require_verification(func):
    """Декоратор для проверки верификации пользователя"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_id = update.effective_user.id
        
        if telegram_id not in verified_users:
            # Пытаемся автоматически проверить
            is_linked, player_data = auth_checker.check_player(telegram_id)
            
            if is_linked:
                minecraft_username = player_data.get('username')
                verified_users[telegram_id] = {
                    'minecraft_username': minecraft_username,
                    'player_data': player_data
                }
            else:
                if hasattr(update, 'callback_query') and update.callback_query:
                    await update.callback_query.answer(
                        "⛔ Сначала пройди верификацию /start",
                        show_alert=True
                    )
                else:
                    await update.message.reply_text(
                        "⛔ Сначала пройди верификацию /start"
                    )
                return
        
        return await func(update, context)
    return wrapper
