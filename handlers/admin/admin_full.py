"""
Админ-панель - полная версия
"""
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, ConversationHandler,
    MessageHandler, CommandHandler, filters
)

from database import db
from utils import require_admin
from keyboards import admin_panel_keyboard, admin_parliament_keyboard, back_button
from config import PARLIAMENT_SEATS, ELECTION_THRESHOLD_PERCENT, CHANNEL_ID

logger = logging.getLogger(__name__)

# Состояния ConversationHandler
VOTING_TYPE, VOTING_TITLE, VOTING_DESC, VOTING_DURATION = range(4)
ELECTION_DURATION = range(1)


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


@require_admin
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика"""
    query = update.callback_query
    await query.answer()
    
    # Подсчитываем статистику
    cursor = db.db.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
    active_users = cursor.fetchone()[0]
    
    cursor = db.db.execute('SELECT COUNT(*) FROM users WHERE is_active = 0')
    inactive_users = cursor.fetchone()[0]
    
    parties = db.get_all_parties(registered_only=False)
    registered_parties = [p for p in parties if p['is_registered']]
    pending_parties = [p for p in parties if not p['is_registered']]
    
    parliament_count = db.get_parliament_count()
    
    active_votings = db.get_active_votings()
    
    cursor = db.db.execute("SELECT COUNT(*) FROM votings WHERE status = 'closed'")
    closed_votings = cursor.fetchone()[0]
    
    text = (
        "📊 <b>СТАТИСТИКА БОТА</b>\n\n"
        "<b>👥 Пользователи:</b>\n"
        f"  Активных: {active_users}\n"
        f"  Деактивированных: {inactive_users}\n\n"
        "<b>🏛️ Партии:</b>\n"
        f"  Зарегистрированных: {len(registered_parties)}\n"
        f"  Набирают членов: {len(pending_parties)}\n\n"
        "<b>🏛️ Парламент:</b>\n"
        f"  Депутатов: {parliament_count}\n\n"
        "<b>🗳️ Голосования:</b>\n"
        f"  Активных: {len(active_votings)}\n"
        f"  Завершённых: {closed_votings}\n"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=back_button("admin_panel"),
        parse_mode='HTML'
    )


@require_admin
async def admin_parliament_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню управления парламентом"""
    query = update.callback_query
    await query.answer()
    
    has_parliament = db.get_parliament_count() > 0
    
    await query.edit_message_text(
        "🏛️ <b>УПРАВЛЕНИЕ ПАРЛАМЕНТОМ</b>",
        reply_markup=admin_parliament_keyboard(has_parliament),
        parse_mode='HTML'
    )


@require_admin
async def dissolve_parliament_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение роспуска парламента"""
    query = update.callback_query
    await query.answer()
    
    count = db.get_parliament_count()
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Распустить", callback_data="do_dissolve_parliament"),
            InlineKeyboardButton("❌ Отмена", callback_data="admin_parliament")
        ]
    ])
    
    await query.edit_message_text(
        f"⚠️ <b>РОСПУСК ПАРЛАМЕНТА</b>\n\n"
        f"Текущий парламент: {count} депутатов\n\n"
        f"Ты точно хочешь распустить парламент?",
        reply_markup=keyboard,
        parse_mode='HTML'
    )


@require_admin
async def do_dissolve_parliament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Роспуск парламента"""
    query = update.callback_query
    await query.answer()
    
    db.clear_parliament()
    
    await query.edit_message_text(
        "✅ <b>Парламент распущен</b>\n\n"
        "Теперь можно провести новые выборы.",
        reply_markup=back_button("admin_panel"),
        parse_mode='HTML'
    )
    
    db.log_action(update.effective_user.id, "Роспуск парламента", "")
    logger.info("✅ Парламент распущен")


@require_admin
async def start_election_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания выборов"""
    query = update.callback_query
    await query.answer()
    
    parties = db.get_all_parties(registered_only=True)
    
    if len(parties) < 2:
        await query.answer(
            "❌ Недостаточно партий для выборов (минимум 2)",
            show_alert=True
        )
        return ConversationHandler.END
    
    await query.edit_message_text(
        "🗳️ <b>СОЗДАНИЕ ВЫБОРОВ</b>\n\n"
        "Введи длительность выборов в часах (например: 48):",
        parse_mode='HTML'
    )
    
    return ELECTION_DURATION


@require_admin
async def election_duration_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение длительности выборов"""
    try:
        hours = int(update.message.text.strip())
        if hours < 1 or hours > 168:
            await update.message.reply_text("❌ Укажи от 1 до 168 часов (неделя)")
            return ELECTION_DURATION
    except ValueError:
        await update.message.reply_text("❌ Введи число!")
        return ELECTION_DURATION
    
    end_date = datetime.now() + timedelta(hours=hours)
    
    # Сначала распускаем старый парламент
    db.clear_parliament()
    
    # Создаём выборы
    election_id = db.create_election(end_date)
    
    # Публикуем в канал
    bot_username = context.bot.username
    deep_link = f"https://t.me/{bot_username}?start=election_{election_id}"
    
    parties = db.get_all_parties(registered_only=True)
    parties_text = "\n".join([f"{i}. {p['name']} ({p['ideology']})" for i, p in enumerate(parties, 1)])
    
    message_text = (
        "🗳️ <b>ОБЪЯВЛЕНИЕ ВЫБОРОВ В ПАРЛАМЕНТ</b>\n\n"
        f"Голосование открыто!\n"
        f"Продлится: {hours} ч.\n"
        f"Мест в парламенте: {PARLIAMENT_SEATS}\n"
        f"Проходной барьер: {ELECTION_THRESHOLD_PERCENT}%\n\n"
        f"<b>Партии-участники:</b>\n{parties_text}\n\n"
        f"Голосуй за партию, не за конкретных людей!\n"
        f"Места распределятся по спискам партий."
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
            db.set_election_channel_message(election_id, msg.message_id)
    except Exception as e:
        logger.error(f"❌ Ошибка публикации в канал: {e}")
    
    await update.message.reply_text(
        f"✅ <b>Выборы запущены!</b>\n\n"
        f"Длительность: {hours} ч.\n"
        f"Ссылка для голосования:\n<code>{deep_link}</code>",
        reply_markup=back_button("admin_panel"),
        parse_mode='HTML'
    )
    
    db.log_action(update.effective_user.id, "Запуск выборов", f"Длительность: {hours}ч")
    logger.info(f"✅ Выборы запущены на {hours} часов")
    
    return ConversationHandler.END


async def cancel_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена админ действия"""
    await update.message.reply_text(
        "❌ Действие отменено.\nИспользуй /start"
    )
    return ConversationHandler.END


def get_handlers():
    """Возвращает обработчики админки"""
    
    # ConversationHandler для создания выборов
    election_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_election_conv, pattern="^admin_election_start$")],
        states={
            ELECTION_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, election_duration_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel_admin_action)],
    )
    
    return [
        CallbackQueryHandler(admin_panel, pattern="^admin_panel$"),
        CallbackQueryHandler(admin_stats, pattern="^admin_stats$"),
        CallbackQueryHandler(admin_parliament_menu, pattern="^admin_parliament$"),
        CallbackQueryHandler(dissolve_parliament_confirm, pattern="^admin_parliament_dissolve$"),
        CallbackQueryHandler(do_dissolve_parliament, pattern="^do_dissolve_parliament$"),
        election_conv,
    ]
