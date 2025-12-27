"""
Обработчики создания партии и вступления
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, 
    CallbackQueryHandler, MessageHandler, 
    CommandHandler, filters
)
from datetime import datetime

from config import verified_users, REGISTRATION_BOT
from utils.decorators import require_verification
from utils.database import db
from utils.auth_checker import auth_checker

# Состояния
PARTY_NAME, PARTY_IDEOLOGY, PARTY_DESCRIPTION = range(3)


@require_verification
async def create_party_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания партии"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    
    # Проверяем есть ли уже партия
    user_party = db.get_user_party(telegram_id)
    if user_party:
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
    """Получение названия партии"""
    name = update.message.text.strip()
    
    if len(name) > 50:
        await update.message.reply_text(
            "❌ Название слишком длинное! Макс. 50 символов.\n"
            "Попробуй ещё раз:"
        )
        return PARTY_NAME
    
    context.user_data['party_name'] = name
    
    await update.message.reply_text(
        f"✅ Название: <b>{name}</b>\n\n"
        f"Шаг 2/3: Выбери идеологию партии:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚔️ Милитаризм", callback_data="ideology_militant")],
            [InlineKeyboardButton("💰 Капитализм", callback_data="ideology_capitalist")],
            [InlineKeyboardButton("🌿 Экология", callback_data="ideology_ecology")],
            [InlineKeyboardButton("🏗️ Строительство", callback_data="ideology_builder")],
            [InlineKeyboardButton("🎓 Наука", callback_data="ideology_science")],
            [InlineKeyboardButton("🤝 Центризм", callback_data="ideology_centrist")],
        ]),
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
    
    ideology = ideology_map.get(query.data, "Центризм")
    context.user_data['party_ideology'] = ideology
    
    await query.edit_message_text(
        f"✅ Идеология: <b>{ideology}</b>\n\n"
        f"Шаг 3/3: Опиши цели и программу партии\n"
        f"(макс. 500 символов)",
        parse_mode='HTML'
    )
    
    return PARTY_DESCRIPTION


async def party_description_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение описания и создание партии"""
    description = update.message.text.strip()
    
    if len(description) > 500:
        await update.message.reply_text(
            "❌ Описание слишком длинное! Макс. 500 символов.\n"
            "Попробуй ещё раз:"
        )
        return PARTY_DESCRIPTION
    
    telegram_id = update.effective_user.id
    username = verified_users[telegram_id]['minecraft_username']
    
    name = context.user_data['party_name']
    ideology = context.user_data['party_ideology']
    
    # Создаём партию
    try:
        party_id, invite_code = db.create_party(
            name=name,
            ideology=ideology,
            description=description,
            leader_telegram_id=telegram_id,
            leader_username=username
        )
        
        bot_username = context.bot.username
        invite_link = f"https://t.me/{bot_username}?start=join_{invite_code}"
        
        keyboard = [
            [InlineKeyboardButton("📋 Управление партией", callback_data=f"manage_party_{party_id}")],
            [InlineKeyboardButton("« В политику", callback_data="section_politics")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🎉 <b>Партия создана!</b>\n\n"
            f"📝 Название: <b>{name}</b>\n"
            f"🎯 Идеология: {ideology}\n"
            f"📄 Описание: {description}\n\n"
            f"⏰ <b>У тебя 24 часа</b> чтобы набрать минимум 10 членов!\n\n"
            f"🔗 Ссылка-приглашение:\n"
            f"<code>{invite_link}</code>\n\n"
            f"Отправь эту ссылку друзьям для вступления.",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка создания партии: {e}\n"
            f"Возможно партия с таким названием уже существует."
        )
    
    return ConversationHandler.END


async def cancel_party_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена создания партии"""
    await update.message.reply_text(
        "❌ Создание партии отменено.\n"
        "Используй /start для возврата в меню."
    )
    return ConversationHandler.END


async def join_party_by_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вступление в партию по ссылке"""
    if not context.args or not context.args[0].startswith('join_'):
        return
    
    invite_code = context.args[0].replace('join_', '')
    telegram_id = update.effective_user.id
    
    # Проверка верификации
    is_linked, player_data = auth_checker.check_player(telegram_id)
    if not is_linked:
        await update.message.reply_text(
            f"❌ Сначала привяжи аккаунт через {REGISTRATION_BOT}\n"
            f"Потом используй ссылку снова."
        )
        return
    
    minecraft_username = player_data.get('username')
    verified_users[telegram_id] = {
        'minecraft_username': minecraft_username,
        'player_data': player_data
    }
    
    # Проверяем есть ли уже партия
    existing_party = db.get_user_party(telegram_id)
    if existing_party:
        await update.message.reply_text(
            f"❌ Ты уже в партии <b>{existing_party['name']}</b>!\n"
            f"Сначала выйди из неё.",
            parse_mode='HTML'
        )
        return
    
    # Получаем партию по коду
    party = db.get_party_by_invite(invite_code)
    if not party:
        await update.message.reply_text("❌ Неверная ссылка-приглашение!")
        return
    
    # Проверяем не истёк ли срок
    if party['registered']:
        status_text = "✅ Зарегистрирована"
    else:
        deadline = datetime.fromisoformat(party['registration_deadline'])
        if datetime.now() > deadline:
            await update.message.reply_text(
                "❌ Срок регистрации партии истёк!\n"
                "Партия не набрала 10 членов за 24 часа."
            )
            return
        time_left = deadline - datetime.now()
        hours = int(time_left.total_seconds() // 3600)
        status_text = f"⏰ Осталось {hours}ч для регистрации"
    
    # Подаём заявку
    success = db.apply_to_party(telegram_id, minecraft_username, party['id'])
    
    if success:
        keyboard = [
            [InlineKeyboardButton("🏛️ Политика", callback_data="section_politics")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📨 <b>Заявка отправлена!</b>\n\n"
            f"Партия: <b>{party['name']}</b>\n"
            f"Идеология: {party['ideology']}\n"
            f"Статус: {status_text}\n\n"
            f"Дождись одобрения главы партии.",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ Ты уже подавал заявку в эту партию!"
        )


def create_party_handler():
    """Создание ConversationHandler для создания партии"""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(create_party_start, pattern="^create_party$")],
        states={
            PARTY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, party_name_received)],
            PARTY_IDEOLOGY: [CallbackQueryHandler(party_ideology_received, pattern="^ideology_")],
            PARTY_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, party_description_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel_party_creation)],
    )
