"""
Обработчики главного меню
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from utils import require_auth
from keyboards import main_menu_keyboard
from config import ADMIN_IDS

logger = logging.getLogger(__name__)


@require_auth
async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    is_admin = telegram_id in ADMIN_IDS
    
    await query.edit_message_text(
        "📋 <b>Главное меню</b>\n\nВыбери раздел:",
        reply_markup=main_menu_keyboard(is_admin),
        parse_mode='HTML'
    )


def get_handlers():
    """Возвращает список обработчиков меню"""
    return [
        CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"),
    ]
