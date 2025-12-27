"""
Обработчики команды /start и верификации
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import verified_users, REGISTRATION_BOT
from utils.auth_checker import auth_checker
from handlers.menu import show_main_menu, show_main_menu_new_message


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - проверка привязки аккаунта"""
    
    # Проверка на приглашение в партию
    if context.args and context.args[0].startswith('join_'):
        from handlers.party_creation import join_party_by_link
        await join_party_by_link(update, context)
        return
    
    user = update.effective_user
    telegram_id = user.id
    
    # Проверяем привязку на сервере
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
        return
    
    minecraft_username = player_data.get('username', 'Неизвестно')
    
    # Если уже подтверждён
    if verified_users.get(telegram_id):
        await show_main_menu(update, context, minecraft_username)
        return
    
    # Создаём кнопки подтверждения
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, это я", callback_data=f"verify_yes_{telegram_id}"),
            InlineKeyboardButton("❌ Нет", callback_data="verify_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎮 <b>Найден игрок на сервере!</b>\n\n"
        f"Minecraft: <code>{minecraft_username}</code>\n"
        f"Telegram ID: <code>{telegram_id}</code>\n\n"
        f"Это ты?",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подтверждения личности"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    telegram_id = update.effective_user.id
    
    if data.startswith("verify_yes"):
        is_linked, player_data = auth_checker.check_player(telegram_id)
        
        if is_linked:
            minecraft_username = player_data.get('username')
            verified_users[telegram_id] = {
                'minecraft_username': minecraft_username,
                'player_data': player_data
            }
            
            await query.edit_message_text(
                f"✅ <b>Верификация успешна!</b>\n\n"
                f"Добро пожаловать, <b>{minecraft_username}</b>!",
                parse_mode='HTML'
            )
            
            await show_main_menu_new_message(query, context, minecraft_username)
        else:
            await query.edit_message_text(
                "❌ Ошибка верификации. Попробуй /start снова"
            )
    
    elif data == "verify_no":
        await query.edit_message_text(
            f"🚫 <b>Верификация отменена</b>\n\n"
            f"Если это не твой аккаунт:\n"
            f"1️⃣ Отвяжи в {REGISTRATION_BOT}\n"
            f"2️⃣ Привяжи правильный\n"
            f"3️⃣ Возвращайся /start",
            parse_mode='HTML'
        )
