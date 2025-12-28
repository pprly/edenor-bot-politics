"""
Выборы в парламент - полная версия
"""
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from database import db
from utils import require_auth, require_admin
from keyboards import confirm_keyboard, back_button
from config import PARLIAMENT_SEATS, ELECTION_THRESHOLD_PERCENT

logger = logging.getLogger(__name__)


async def handle_election_deeplink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка deep link для выборов"""
    args = context.args
    if not args or not args[0].startswith('election_'):
        return
    
    election_id = int(args[0].replace('election_', ''))
    
    # Проверяем авторизацию
    telegram_id = update.effective_user.id
    user = db.get_user(telegram_id)
    
    if not user:
        await update.message.reply_text(
            "❌ Сначала пройди верификацию /start"
        )
        return
    
    election = db.get_election_by_id(election_id)
    
    if not election or election['status'] != 'active':
        await update.message.reply_text("❌ Выборы не найдены или завершены")
        return
    
    # Проверяем не голосовал ли уже
    if db.has_voted_in_election(election_id, telegram_id):
        await update.message.reply_text(
            "✅ Ты уже проголосовал на этих выборах!\n\n"
            "Результаты будут объявлены после завершения голосования."
        )
        return
    
    # Показываем список партий
    parties = db.get_all_parties(registered_only=True)
    
    if not parties:
        await update.message.reply_text("❌ Нет зарегистрированных партий")
        return
    
    text = "🗳️ <b>ВЫБОРЫ В ПАРЛАМЕНТ</b>\n\n"
    text += f"Мест в парламенте: {PARLIAMENT_SEATS}\n"
    text += f"Проходной барьер: {ELECTION_THRESHOLD_PERCENT}%\n\n"
    text += "Выбери партию:\n\n"
    
    keyboard = []
    for i, party in enumerate(parties, 1):
        text += f"{i}. <b>{party['name']}</b> ({party['ideology']})\n"
        keyboard.append([
            InlineKeyboardButton(
                f"{i}. {party['name']}",
                callback_data=f"elect_vote_{election_id}_{party['id']}"
            )
        ])
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


@require_auth
async def vote_for_party(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Голосование за партию"""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    election_id = int(data_parts[2])
    party_id = int(data_parts[3])
    
    telegram_id = update.effective_user.id
    
    # Проверяем не голосовал ли уже
    if db.has_voted_in_election(election_id, telegram_id):
        await query.answer("❌ Ты уже голосовал!", show_alert=True)
        return
    
    party = db.get_party_by_id(party_id)
    
    # Подтверждение
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_elect_{election_id}_{party_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"election_view_{election_id}")
        ]
    ])
    
    await query.edit_message_text(
        f"⚠️ <b>Подтверди свой выбор</b>\n\n"
        f"Ты голосуешь за партию:\n"
        f"<b>{party['name']}</b>\n\n"
        f"❗ Это действие необратимо!",
        reply_markup=keyboard,
        parse_mode='HTML'
    )


@require_auth
async def confirm_election_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение голоса на выборах"""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    election_id = int(data_parts[2])
    party_id = int(data_parts[3])
    
    telegram_id = update.effective_user.id
    
    # Голосуем
    success = db.vote_in_election(election_id, telegram_id, party_id)
    
    if not success:
        await query.answer("❌ Ошибка голосования", show_alert=True)
        return
    
    party = db.get_party_by_id(party_id)
    
    await query.edit_message_text(
        f"✅ <b>Твой голос учтён!</b>\n\n"
        f"Ты проголосовал за: <b>{party['name']}</b>\n\n"
        f"Спасибо за участие в выборах!\n"
        f"Результаты будут объявлены после завершения.",
        parse_mode='HTML'
    )
    
    db.log_action(telegram_id, "Голосование на выборах", f"Партия: {party['name']}")
    logger.info(f"✅ Голос: {telegram_id} → {party['name']}")


def get_handlers():
    """Возвращает обработчики выборов"""
    return [
        CallbackQueryHandler(vote_for_party, pattern="^elect_vote_"),
        CallbackQueryHandler(confirm_election_vote, pattern="^confirm_elect_"),
    ]
