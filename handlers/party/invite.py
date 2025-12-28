"""
Приглашения в партию
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
            f"Сначала выйди из неё через меню партии",
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
        CommandHandler("party_link", party_link_command),
    ]
