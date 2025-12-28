"""
Админ-панель
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from utils import require_admin
from keyboards import admin_panel_keyboard

logger = logging.getLogger(__name__)

@require_admin
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ-панель"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "⚙️ <b>АДМИН-ПАНЕЛЬ</b>\n\nУправление ботом и системой",
        reply_markup=admin_panel_keyboard(),
        parse_mode='HTML'
    )

def get_handlers():
    return [
        CallbackQueryHandler(admin_panel, pattern="^admin_panel$"),
    ]
