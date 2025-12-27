"""
Обработчики раздела Торговля (заглушка)
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils.decorators import require_verification


@require_verification
async def trade_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню торговли"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("« Назад", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💰 <b>ТОРГОВЛЯ</b>\n\n"
        "🚧 Раздел в разработке...\n\n"
        "Скоро здесь будет:\n"
        "• Маркетплейс\n"
        "• Аукционы\n"
        "• Биржа\n"
        "• Контракты",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
