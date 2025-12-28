"""
Приглашения в партию
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from database import db
from utils import require_auth, send_notification
from keyboards import back_button

logger = logging.getLogger(__name__)


async def handle_party_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка deep link приглашения в партию"""
    args = context.args
    if not args or not args[0].startswith('join_'):
        return
    
    invite_code = args[0].replace('join_', '')
    telegram_id = update.effective_user.id
    
    # Проверяем авторизацию
    user = db.get_user(telegram_id)
    if not user:
        from utils import auth_checker
        from config import REGISTRATION_BOT
        
        is_linked, player_data = auth_checker.check_player(telegram_id)
        if not is_linked:
            await update.message.reply_text(
                f"❌ Сначала пройди верификацию!\n\n"
                f"1. Привяжи Telegram через {REGISTRATION_BOT}\n"
                f"2. Напиши /start"
            )
            return
        
        # Добавляем пользователя
        minecraft_username = player_data.get('username')
        db.add_user(telegram_id, minecraft_username)
    
    # Проверяем есть ли уже в партии
    current_party = db.get_user_party(telegram_id)
    if current_party:
        await update.message.reply_text(
            f"❌ Ты уже в партии <b>{current_party['name']}</b>!\n\n"
            f"Сначала выйди из неё: /party_leave",
            parse_mode='HTML'
        )
        return
    
    # Находим партию по коду
    party = db.get_party_by_invite(invite_code)
    if not party:
        await update.message.reply_text("❌ Партия не найдена или ссылка устарела")
        return
    
    # Подаём заявку
    success = db.apply_to_party(telegram_id, party['id'])
    
    if not success:
        await update.message.reply_text("❌ Заявка уже подана ранее")
        return
    
    # Уведомляем пользователя
    await update.message.reply_text(
        f"✅ <b>Заявка отправлена!</b>\n\n"
        f"Партия: <b>{party['name']}</b>\n"
        f"Идеология: {party['ideology']}\n\n"
        f"Дождись одобрения главы партии.",
        parse_mode='HTML'
    )
    
    # Уведомляем главу партии
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    user_info = db.get_user(telegram_id)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("👥 Посмотреть заявки", callback_data=f"party_applications_{party['id']}")
    ]])
    
    await send_notification(
        context.bot,
        party['leader_telegram_id'],
        f"📨 <b>Новая заявка в партию!</b>\n\n"
        f"Игрок <b>{user_info['minecraft_username']}</b> хочет вступить в партию.\n\n"
        f"Проверь заявки в меню партии или нажми кнопку ниже:",
        parse_mode='HTML'
    )
    
    db.log_action(telegram_id, "Заявка в партию", f"Партия: {party['name']}")
    logger.info(f"✅ Заявка: {user_info['minecraft_username']} → {party['name']}")


@require_auth
async def party_invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /party_invite nickname - пригласить игрока"""
    telegram_id = update.effective_user.id
    party = db.get_user_party(telegram_id)
    
    if not party:
        await update.message.reply_text("❌ Ты не в партии!")
        return
    
    # Только глава может приглашать
    if party['leader_telegram_id'] != telegram_id:
        await update.message.reply_text("❌ Только глава партии может приглашать!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Укажи никнейм игрока!\n\n"
            "Использование: <code>/party_invite nickname</code>",
            parse_mode='HTML'
        )
        return
    
    target_nickname = context.args[0]
    
    # Проверяем существует ли игрок
    from utils import auth_checker
    
    # Ищем игрока в БД по никнейму
    cursor = db.db.execute(
        'SELECT telegram_id FROM users WHERE minecraft_username = ?',
        (target_nickname,)
    )
    target_user = cursor.fetchone()
    
    if not target_user:
        await update.message.reply_text(
            f"❌ Игрок <b>{target_nickname}</b> не найден в боте.\n\n"
            f"Отправь ему ссылку-приглашение через /party_link",
            parse_mode='HTML'
        )
        return
    
    target_telegram_id = target_user[0]
    
    # Проверяем не в партии ли уже
    target_party = db.get_user_party(target_telegram_id)
    if target_party:
        await update.message.reply_text(
            f"❌ Игрок уже в партии <b>{target_party['name']}</b>",
            parse_mode='HTML'
        )
        return
    
    # Отправляем приглашение
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"accept_invite_{party['id']}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_invite_{party['id']}")
        ]
    ])
    
    user_info = db.get_user(telegram_id)
    
    await send_notification(
        context.bot,
        target_telegram_id,
        f"📨 <b>Приглашение в партию!</b>\n\n"
        f"<b>{user_info['minecraft_username']}</b> приглашает тебя в партию:\n\n"
        f"🏛️ <b>{party['name']}</b>\n"
        f"🎯 {party['ideology']}\n"
        f"👥 Членов: {party['members_count']}\n\n"
        f"📋 {party['description'][:100]}...",
        parse_mode='HTML'
    )
    
    await update.message.reply_text(
        f"✅ Приглашение отправлено игроку <b>{target_nickname}</b>",
        parse_mode='HTML'
    )
    
    logger.info(f"✅ Приглашение: {party['name']} → {target_nickname}")


@require_auth
async def accept_invite_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принять приглашение в партию"""
    query = update.callback_query
    await query.answer()
    
    party_id = int(query.data.split('_')[2])
    telegram_id = update.effective_user.id
    
    # Проверяем не в партии ли уже
    current_party = db.get_user_party(telegram_id)
    if current_party:
        await query.edit_message_text(
            f"❌ Ты уже в партии <b>{current_party['name']}</b>",
            parse_mode='HTML'
        )
        return
    
    party = db.get_party_by_id(party_id)
    if not party:
        await query.edit_message_text("❌ Партия не найдена")
        return
    
    # Получаем текущее количество членов для позиции в списке
    members = db.get_party_members(party_id)
    position = len(members) + 1
    
    # Добавляем в партию
    db.db.execute(
        'INSERT INTO party_members (telegram_id, party_id, list_position) VALUES (?, ?, ?)',
        (telegram_id, party_id, position)
    )
    db.db.execute(
        'UPDATE parties SET members_count = members_count + 1 WHERE id = ?',
        (party_id,)
    )
    db.db.commit()
    
    await query.edit_message_text(
        f"✅ <b>Ты вступил в партию!</b>\n\n"
        f"Партия: <b>{party['name']}</b>\n"
        f"Твоя позиция в списке: {position}",
        parse_mode='HTML'
    )
    
    # Уведомляем главу
    user_info = db.get_user(telegram_id)
    await send_notification(
        context.bot,
        party['leader_telegram_id'],
        f"✅ <b>{user_info['minecraft_username']}</b> принял приглашение и вступил в партию!"
    )
    
    db.log_action(telegram_id, "Вступление в партию", f"Партия: {party['name']}")


@require_auth
async def decline_invite_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отклонить приглашение"""
    query = update.callback_query
    await query.answer()
    
    party_id = int(query.data.split('_')[2])
    party = db.get_party_by_id(party_id)
    
    await query.edit_message_text(
        f"❌ Ты отклонил приглашение в партию <b>{party['name'] if party else 'неизвестную'}</b>",
        parse_mode='HTML'
    )


@require_auth
async def party_link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /party_link - получить ссылку-приглашение"""
    telegram_id = update.effective_user.id
    party = db.get_user_party(telegram_id)
    
    if not party:
        await update.message.reply_text("❌ Ты не в партии!")
        return
    
    bot_username = context.bot.username
    invite_link = f"https://t.me/{bot_username}?start=join_{party['invite_code']}"
    
    await update.message.reply_text(
        f"🔗 <b>Ссылка-приглашение в партию</b>\n\n"
        f"Партия: <b>{party['name']}</b>\n\n"
        f"<code>{invite_link}</code>\n\n"
        f"Отправь эту ссылку друзьям для вступления в партию!",
        parse_mode='HTML'
    )


def get_handlers():
    """Возвращает обработчики приглашений"""
    return [
        CommandHandler("party_invite", party_invite_command),
        CommandHandler("party_link", party_link_command),
        CallbackQueryHandler(accept_invite_handler, pattern="^accept_invite_"),
        CallbackQueryHandler(decline_invite_handler, pattern="^decline_invite_"),
    ]
