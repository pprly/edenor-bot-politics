"""
Обработчик профиля пользователя
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from database import db
from utils import require_auth
from keyboards import back_button

logger = logging.getLogger(__name__)


@require_auth
async def profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр профиля"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    user = db.get_user(telegram_id)
    
    if not user:
        await query.answer("❌ Ошибка загрузки профиля", show_alert=True)
        return
    
    # Получаем информацию о партии
    party = db.get_user_party(telegram_id)
    is_deputy = db.is_deputy(telegram_id)
    
    status_lines = []
    
    if party:
        role = "👑 Глава" if party['leader_telegram_id'] == telegram_id else "👤 Член"
        status_lines.append(f"Партия: <b>{party['name']}</b> ({role})")
    else:
        status_lines.append("Партия: <i>Не состоит</i>")
    
    if is_deputy:
        status_lines.append("Должность: <b>🏛️ Депутат</b>")
    
    status_text = "\n".join(status_lines)
    
    await query.edit_message_text(
        f"👤 <b>ПРОФИЛЬ</b>\n\n"
        f"Minecraft: <code>{user['minecraft_username']}</code>\n"
        f"Telegram ID: <code>{telegram_id}</code>\n"
        f"Верифицирован: {user['verified_at'][:10]}\n\n"
        f"{status_text}",
        reply_markup=back_button("main_menu"),
        parse_mode='HTML'
    )


def get_handlers():
    """Возвращает список обработчиков профиля"""
    return [
        CallbackQueryHandler(profile_menu, pattern="^menu_profile$"),
    ]
