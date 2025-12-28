"""
Создание партии - ConversationHandler
"""
import logging
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler,
    CallbackQueryHandler, MessageHandler,
    CommandHandler, filters
)

from database import db
from utils import require_auth, send_notification, notify_party_members
from keyboards import ideology_keyboard, back_button
from config import PARTY_MIN_MEMBERS, PARTY_CREATION_TIME_MINUTES

logger = logging.getLogger(__name__)

# Состояния
PARTY_NAME, PARTY_IDEOLOGY, PARTY_IDEOLOGY_CUSTOM, PARTY_DESCRIPTION = range(4)


@require_auth
async def create_party_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания партии"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    
    if db.get_user_party(telegram_id):
        await query.answer("❌ Ты уже в партии!", show_alert=True)
        return ConversationHandler.END
    
    await query.edit_message_text(
        "🏛️ <b>СОЗДАНИЕ ПАРТИИ</b>\n\n"
        "Шаг 1/3: Введи название партии\n"
        "(макс. 50 символов)\n\n"
        "Отправь /cancel для отмены",
        parse_mode='HTML'
    )
    
    return PARTY_NAME


async def party_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение названия"""
    name = update.message.text.strip()
    
    if len(name) > 50:
        await update.message.reply_text(
            "❌ Название слишком длинное! Макс. 50 символов.\nПопробуй ещё раз:"
        )
        return PARTY_NAME
    
    context.user_data['party_name'] = name
    
    await update.message.reply_text(
        f"✅ Название: <b>{name}</b>\n\nШаг 2/3: Выбери идеологию:",
        reply_markup=ideology_keyboard(),
        parse_mode='HTML'
    )
    
    return PARTY_IDEOLOGY


async def party_ideology_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение идеологии"""
    query = update.callback_query
    await query.answer()
    
    ideology_map = {
        "ideology_militant": "⚔️ Милитаризм",
        "ideology_capitalist": "💰 Капитализм",
        "ideology_ecology": "🌿 Экология",
        "ideology_builder": "🏗️ Строительство",
        "ideology_science": "🎓 Наука",
        "ideology_centrist": "🤝 Центризм"
    }
    
    if query.data == "ideology_custom":
        await query.edit_message_text(
            "✏️ Введи свою идеологию (макс. 30 символов):"
        )
        return PARTY_IDEOLOGY_CUSTOM
    
    ideology = ideology_map.get(query.data, "Центризм")
    context.user_data['party_ideology'] = ideology
    
    await query.edit_message_text(
        f"✅ Идеология: <b>{ideology}</b>\n\n"
        f"Шаг 3/3: Опиши цели и программу партии (макс. 500 символов)",
        parse_mode='HTML'
    )
    
    return PARTY_DESCRIPTION


async def party_ideology_custom_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение кастомной идеологии"""
    custom_ideology = update.message.text.strip()
    
    if len(custom_ideology) > 30:
        await update.message.reply_text(
            "❌ Слишком длинная идеология! Макс. 30 символов.\nПопробуй ещё раз:"
        )
        return PARTY_IDEOLOGY_CUSTOM
    
    context.user_data['party_ideology'] = custom_ideology
    
    await update.message.reply_text(
        f"✅ Идеология: <b>{custom_ideology}</b>\n\n"
        f"Шаг 3/3: Опиши цели и программу партии (макс. 500 символов)",
        parse_mode='HTML'
    )
    
    return PARTY_DESCRIPTION


async def party_description_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение описания и создание партии"""
    description = update.message.text.strip()
    
    if len(description) > 500:
        await update.message.reply_text(
            "❌ Описание слишком длинное! Макс. 500 символов.\nПопробуй ещё раз:"
        )
        return PARTY_DESCRIPTION
    
    telegram_id = update.effective_user.id
    name = context.user_data['party_name']
    ideology = context.user_data['party_ideology']
    
    try:
        party_id, invite_code = db.create_party(
            name=name,
            ideology=ideology,
            description=description,
            leader_telegram_id=telegram_id,
            deadline_minutes=PARTY_CREATION_TIME_MINUTES
        )
        
        bot_username = context.bot.username
        invite_link = f"https://t.me/{bot_username}?start=join_{invite_code}"
        
        db.log_action(telegram_id, "Создание партии", f"Партия: {name}")
        
        await update.message.reply_text(
            f"🎉 <b>Партия создана!</b>\n\n"
            f"📝 Название: <b>{name}</b>\n"
            f"🎯 Идеология: {ideology}\n\n"
            f"⏰ У тебя <b>{PARTY_CREATION_TIME_MINUTES} минут</b> чтобы набрать минимум {PARTY_MIN_MEMBERS} членов!\n\n"
            f"🔗 Ссылка-приглашение:\n<code>{invite_link}</code>\n\n"
            f"Отправь её друзьям или используй команду:\n"
            f"<code>/party invite nickname</code>",
            reply_markup=back_button("party_my"),
            parse_mode='HTML'
        )
        
        logger.info(f"✅ Партия создана: {name} by {telegram_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания партии: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")
    
    return ConversationHandler.END


async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена создания"""
    await update.message.reply_text(
        "❌ Создание партии отменено.\nИспользуй /start для возврата в меню."
    )
    return ConversationHandler.END


def get_handler():
    """Возвращает ConversationHandler для создания партии"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(create_party_start, pattern="^party_create$")],
        states={
            PARTY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, party_name_received)],
            PARTY_IDEOLOGY: [CallbackQueryHandler(party_ideology_received, pattern="^ideology_")],
            PARTY_IDEOLOGY_CUSTOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, party_ideology_custom_received)],
            PARTY_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, party_description_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel_creation)],
    )
