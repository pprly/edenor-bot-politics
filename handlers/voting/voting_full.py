"""
Голосования - полная версия
"""
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, ConversationHandler,
    MessageHandler, CommandHandler, filters
)

from database import db
from utils import require_auth, require_admin, require_deputy
from keyboards import voting_keyboard, back_button
from config import CHANNEL_ID

logger = logging.getLogger(__name__)

# Состояния
VOTING_TYPE, VOTING_TITLE, VOTING_DESC, VOTING_DURATION = range(4)


async def handle_vote_deeplink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка deep link для голосования"""
    args = context.args
    if not args or not args[0].startswith('vote_'):
        return
    
    voting_id = int(args[0].replace('vote_', ''))
    
    telegram_id = update.effective_user.id
    user = db.get_user(telegram_id)
    
    if not user:
        await update.message.reply_text("❌ Сначала пройди верификацию /start")
        return
    
    voting = db.get_voting_by_id(voting_id)
    
    if not voting or voting['status'] != 'active':
        await update.message.reply_text("❌ Голосование не найдено или завершено")
        return
    
    # Проверяем права
    if voting['voting_type'] == 'parliament':
        if not db.is_deputy(telegram_id):
            await update.message.reply_text(
                "❌ <b>Парламентское голосование</b>\n\n"
                "Голосовать могут только депутаты парламента.",
                parse_mode='HTML'
            )
            return
    
    # Проверяем не голосовал ли уже
    if db.has_voted(voting_id, telegram_id):
        await update.message.reply_text(
            "✅ Ты уже проголосовал!\n\n"
            "Результаты будут объявлены после завершения."
        )
        return
    
    # Показываем голосование
    end_date = datetime.fromisoformat(voting['end_date'])
    time_left = end_date - datetime.now()
    hours_left = int(time_left.total_seconds() / 3600)
    
    text = (
        f"🗳️ <b>{voting['title']}</b>\n\n"
        f"{voting['description']}\n\n"
        f"⏰ Осталось: ~{hours_left} ч.\n"
        f"📊 За: {voting['votes_for']} | Против: {voting['votes_against']}"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=voting_keyboard(voting_id),
        parse_mode='HTML'
    )


@require_auth
async def vote_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка голоса"""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    voting_id = int(data_parts[1])
    vote_type = data_parts[2]  # 'for' или 'against'
    
    telegram_id = update.effective_user.id
    voting = db.get_voting_by_id(voting_id)
    
    if not voting or voting['status'] != 'active':
        await query.answer("❌ Голосование завершено", show_alert=True)
        return
    
    # Проверяем права
    if voting['voting_type'] == 'parliament' and not db.is_deputy(telegram_id):
        await query.answer("❌ Только для депутатов!", show_alert=True)
        return
    
    # Проверяем не голосовал ли
    if db.has_voted(voting_id, telegram_id):
        await query.answer("❌ Ты уже голосовал!", show_alert=True)
        return
    
    # Подтверждение
    vote_text = "ЗА" if vote_type == 'for' else "ПРОТИВ"
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_vote_{voting_id}_{vote_type}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"voting_view_{voting_id}")
        ]
    ])
    
    await query.edit_message_text(
        f"⚠️ <b>Подтверди свой голос</b>\n\n"
        f"Голосование: <b>{voting['title']}</b>\n\n"
        f"Твой голос: <b>{vote_text}</b>\n\n"
        f"❗ Это действие необратимо!",
        reply_markup=keyboard,
        parse_mode='HTML'
    )


@require_auth
async def confirm_vote_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение голоса"""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    voting_id = int(data_parts[2])
    vote_type = data_parts[3]
    
    telegram_id = update.effective_user.id
    
    # Голосуем
    success = db.vote(voting_id, telegram_id, vote_type)
    
    if not success:
        await query.answer("❌ Ошибка голосования", show_alert=True)
        return
    
    voting = db.get_voting_by_id(voting_id)
    vote_text = "ЗА" if vote_type == 'for' else "ПРОТИВ"
    
    await query.edit_message_text(
        f"✅ <b>Твой голос учтён!</b>\n\n"
        f"Голосование: <b>{voting['title']}</b>\n"
        f"Твой голос: <b>{vote_text}</b>\n\n"
        f"Спасибо за участие!",
        parse_mode='HTML'
    )
    
    db.log_action(telegram_id, "Голосование", f"{voting['title']}: {vote_text}")
    logger.info(f"✅ Голос: {telegram_id} → {voting['title']} ({vote_text})")


@require_auth
async def active_votings_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список активных голосований"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    is_deputy = db.is_deputy(telegram_id)
    
    votings = db.get_active_votings()
    
    if not votings:
        await query.edit_message_text(
            "🗳️ <b>ГОЛОСОВАНИЯ</b>\n\n"
            "Нет активных голосований.",
            reply_markup=back_button("main_menu"),
            parse_mode='HTML'
        )
        return
    
    text = "🗳️ <b>АКТИВНЫЕ ГОЛОСОВАНИЯ</b>\n\n"
    keyboard = []
    
    for voting in votings:
        vote_type_icon = "🏛️" if voting['voting_type'] == 'parliament' else "👥"
        
        # Проверяем доступ
        if voting['voting_type'] == 'parliament' and not is_deputy:
            continue
        
        # Проверяем не голосовал ли
        has_voted = db.has_voted(voting['id'], telegram_id)
        status = " ✅" if has_voted else ""
        
        keyboard.append([
            InlineKeyboardButton(
                f"{vote_type_icon} {voting['title'][:30]}{status}",
                callback_data=f"voting_view_{voting['id']}"
            )
        ])
    
    if not keyboard:
        text += "Нет доступных голосований для тебя."
    
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="main_menu")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


@require_admin
async def create_voting_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания голосования"""
    query = update.callback_query
    await query.answer()
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏛️ Парламентское", callback_data="voting_type_parliament")],
        [InlineKeyboardButton("👥 Общее", callback_data="voting_type_public")],
        [InlineKeyboardButton("« Отмена", callback_data="admin_panel")]
    ])
    
    await query.edit_message_text(
        "🗳️ <b>СОЗДАНИЕ ГОЛОСОВАНИЯ</b>\n\n"
        "Шаг 1/4: Выбери тип голосования",
        reply_markup=keyboard,
        parse_mode='HTML'
    )
    
    return VOTING_TYPE


@require_admin
async def voting_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбран тип голосования"""
    query = update.callback_query
    await query.answer()
    
    voting_type = 'parliament' if 'parliament' in query.data else 'public'
    context.user_data['voting_type'] = voting_type
    
    type_text = "Парламентское" if voting_type == 'parliament' else "Общее"
    
    await query.edit_message_text(
        f"✅ Тип: <b>{type_text}</b>\n\n"
        f"Шаг 2/4: Введи название голосования (макс. 100 символов):",
        parse_mode='HTML'
    )
    
    return VOTING_TITLE


@require_admin
async def voting_title_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получено название"""
    title = update.message.text.strip()
    
    if len(title) > 100:
        await update.message.reply_text("❌ Слишком длинное! Макс. 100 символов.")
        return VOTING_TITLE
    
    context.user_data['voting_title'] = title
    
    await update.message.reply_text(
        f"✅ Название: <b>{title}</b>\n\n"
        f"Шаг 3/4: Введи описание (макс. 500 символов):",
        parse_mode='HTML'
    )
    
    return VOTING_DESC


@require_admin
async def voting_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получено описание"""
    desc = update.message.text.strip()
    
    if len(desc) > 500:
        await update.message.reply_text("❌ Слишком длинное! Макс. 500 символов.")
        return VOTING_DESC
    
    context.user_data['voting_desc'] = desc
    
    await update.message.reply_text(
        f"✅ Описание сохранено\n\n"
        f"Шаг 4/4: Введи длительность в часах (например: 24):",
        parse_mode='HTML'
    )
    
    return VOTING_DURATION


@require_admin
async def voting_duration_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получена длительность и создание голосования"""
    try:
        hours = int(update.message.text.strip())
        if hours < 1 or hours > 168:
            await update.message.reply_text("❌ Укажи от 1 до 168 часов")
            return VOTING_DURATION
    except ValueError:
        await update.message.reply_text("❌ Введи число!")
        return VOTING_DURATION
    
    telegram_id = update.effective_user.id
    voting_type = context.user_data['voting_type']
    title = context.user_data['voting_title']
    desc = context.user_data['voting_desc']
    
    end_date = datetime.now() + timedelta(hours=hours)
    
    # Создаём голосование
    voting_id = db.create_voting(title, desc, voting_type, telegram_id, end_date)
    
    # Публикуем в канал
    bot_username = context.bot.username
    deep_link = f"https://t.me/{bot_username}?start=vote_{voting_id}"
    
    type_text = "🏛️ Парламентское" if voting_type == 'parliament' else "👥 Общее"
    voters_text = "Голосуют только депутаты" if voting_type == 'parliament' else "Голосуют все игроки"
    
    message_text = (
        f"{type_text} ГОЛОСОВАНИЕ\n\n"
        f"<b>{title}</b>\n\n"
        f"{desc}\n\n"
        f"{voters_text}\n"
        f"Продлится: {hours} ч."
    )
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🗳️ ГОЛОСОВАТЬ", url=deep_link)
    ]])
    
    try:
        if CHANNEL_ID:
            msg = await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=message_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            db.set_voting_channel_message(voting_id, msg.message_id)
    except Exception as e:
        logger.error(f"❌ Ошибка публикации: {e}")
    
    await update.message.reply_text(
        f"✅ <b>Голосование создано!</b>\n\n"
        f"Тип: {type_text}\n"
        f"Название: {title}\n"
        f"Длительность: {hours} ч.\n\n"
        f"Ссылка:\n<code>{deep_link}</code>",
        reply_markup=back_button("admin_panel"),
        parse_mode='HTML'
    )
    
    db.log_action(telegram_id, "Создание голосования", title)
    logger.info(f"✅ Голосование создано: {title} ({voting_type})")
    
    return ConversationHandler.END


async def cancel_voting_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена создания"""
    await update.message.reply_text("❌ Создание отменено. Используй /start")
    return ConversationHandler.END


def get_handlers():
    """Возвращает обработчики голосований"""
    
    # ConversationHandler для создания голосования
    create_voting_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_voting_start, pattern="^admin_create_voting$")],
        states={
            VOTING_TYPE: [CallbackQueryHandler(voting_type_selected, pattern="^voting_type_")],
            VOTING_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, voting_title_received)],
            VOTING_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, voting_desc_received)],
            VOTING_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, voting_duration_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel_voting_creation)],
    )
    
    return [
        CallbackQueryHandler(vote_handler, pattern="^vote_\\d+_(for|against)$"),
        CallbackQueryHandler(confirm_vote_handler, pattern="^confirm_vote_"),
        CallbackQueryHandler(active_votings_list, pattern="^active_votings$"),
        create_voting_conv,
    ]
