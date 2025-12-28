"""
Обработчик команды /start
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from database import db
from utils import auth_checker
from keyboards import main_menu_keyboard
from config import REGISTRATION_BOT, ADMIN_IDS

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - проверка и верификация"""
    user = update.effective_user
    telegram_id = user.id
    
    # Проверка на deep link (приглашение в партию)
    if context.args and context.args[0].startswith('join_'):
        from handlers.party.invite import handle_party_invite
        await handle_party_invite(update, context)
        return
    
    # Проверка на deep link (просмотр партии)
    if context.args and context.args[0].startswith('party_'):
        from handlers.party.view import handle_party_deeplink
        await handle_party_deeplink(update, context)
        return
    
    # Проверка на deep link (голосование)
    if context.args and context.args[0].startswith('vote_'):
        from handlers.voting.participate import handle_vote_deeplink
        await handle_vote_deeplink(update, context)
        return
    
    # Проверка на deep link (выборы)
    if context.args and context.args[0].startswith('election_'):
        from handlers.parliament.elections import handle_election_deeplink
        await handle_election_deeplink(update, context)
        return
    
    # Проверяем есть ли пользователь в БД
    user_data = db.get_user(telegram_id)
    
    if user_data:
        # Пользователь уже есть
        is_admin = telegram_id in ADMIN_IDS
        await update.message.reply_text(
            f"👋 С возвращением, <b>{user_data['minecraft_username']}</b>!",
            reply_markup=main_menu_keyboard(is_admin),
            parse_mode='HTML'
        )
        logger.info(f"👤 Возврат пользователя: {user_data['minecraft_username']}")
        return
    
    # Новый пользователь - проверяем через API
    is_linked, player_data = auth_checker.check_player(telegram_id)
    
    if not is_linked:
        await update.message.reply_text(
            "❌ <b>Аккаунт не привязан к серверу</b>\n\n"
            f"Для использования бота:\n"
            f"1️⃣ Привяжи Telegram к игровому аккаунту\n"
            f"2️⃣ Перейди в бот: {REGISTRATION_BOT}\n"
            f"3️⃣ Следуй инструкциям\n\n"
            f"После привязки возвращайся и напиши /start",
            parse_mode='HTML'
        )
        logger.info(f"❌ Попытка входа неверифицированного пользователя: {telegram_id}")
        return
    
    # Добавляем пользователя в БД
    minecraft_username = player_data.get('username', 'Неизвестно')
    db.add_user(telegram_id, minecraft_username)
    db.log_action(telegram_id, "Регистрация", f"Новый пользователь: {minecraft_username}")
    
    is_admin = telegram_id in ADMIN_IDS
    
    await update.message.reply_text(
        f"✅ <b>Добро пожаловать, {minecraft_username}!</b>\n\n"
        f"🎮 Ты успешно верифицирован\n"
        f"💬 Telegram ID: <code>{telegram_id}</code>\n\n"
        f"Выбери раздел:",
        reply_markup=main_menu_keyboard(is_admin),
        parse_mode='HTML'
    )
    
    logger.info(f"✅ Новый пользователь добавлен: {minecraft_username} ({telegram_id})")


def get_handler():
    """Возвращает обработчик команды /start"""
    return CommandHandler("start", start_command)

    