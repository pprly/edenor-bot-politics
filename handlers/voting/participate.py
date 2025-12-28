"""
Участие в голосованиях
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def handle_vote_deeplink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка deep link для голосования"""
    # TODO: Реализовать голосования
    await update.message.reply_text("🚧 Функция в разработке")
