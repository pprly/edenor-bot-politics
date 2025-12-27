"""
Обработчики раздела Развлечения (заглушка)
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils.decorators import require_verification


@require_verification
async def entertainment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню развлечений"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("« Назад", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎲 <b>РАЗВЛЕЧЕНИЯ</b>\n\n"
        "🚧 Раздел в разработке...\n\n"
        "Скоро здесь будет:\n"
        "• Дуэли\n"
        "• Казино\n"
        "• Ставки\n"
        "• Лотерея",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
