"""
Заглушки для функций в разработке
"""
from telegram import Update
from telegram.ext import ContextTypes


async def placeholder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Временная заглушка"""
    query = update.callback_query
    await query.answer("🚧 В разработке", show_alert=True)
