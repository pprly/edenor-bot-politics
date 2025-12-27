"""
Обработчики главного меню и профиля
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import verified_users
from utils.decorators import require_verification
from utils.database import db


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, username: str):
    """Главное меню для команды /start"""
    keyboard = [
        [InlineKeyboardButton("🏛️ Политика", callback_data="section_politics")],
        [InlineKeyboardButton("💰 Торговля", callback_data="section_trade")],
        [InlineKeyboardButton("🎲 Развлечения", callback_data="section_entertainment")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎮 <b>Добро пожаловать, {username}!</b>\n\n"
        f"Выбери раздел:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def show_main_menu_new_message(query, context: ContextTypes.DEFAULT_TYPE, username: str):
    """Главное меню (новое сообщение после верификации)"""
    keyboard = [
        [InlineKeyboardButton("🏛️ Политика", callback_data="section_politics")],
        [InlineKeyboardButton("💰 Торговля", callback_data="section_trade")],
        [InlineKeyboardButton("🎲 Развлечения", callback_data="section_entertainment")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(
        f"📋 <b>Главное меню</b>\n\nВыбери раздел:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


@require_verification
async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню через callback"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    username = verified_users[telegram_id]['minecraft_username']
    
    keyboard = [
        [InlineKeyboardButton("🏛️ Политика", callback_data="section_politics")],
        [InlineKeyboardButton("💰 Торговля", callback_data="section_trade")],
        [InlineKeyboardButton("🎲 Развлечения", callback_data="section_entertainment")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🎮 <b>Главное меню</b>\n\nВыбери раздел:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


@require_verification
async def profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Профиль пользователя"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    username = verified_users[telegram_id]['minecraft_username']
    
    party = db.get_user_party(telegram_id)
    is_deputy = db.is_deputy(telegram_id)
    
    status = []
    if party:
        role = "👑 Глава" if party['leader_telegram_id'] == telegram_id else "👤 Член"
        status.append(f"Партия: <b>{party['name']}</b> ({role})")
    if is_deputy:
        status.append("Должность: <b>Депутат</b>")
    
    status_text = "\n".join(status) if status else "Нет партии"
    
    keyboard = [[InlineKeyboardButton("« Назад", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"👤 <b>ПРОФИЛЬ</b>\n\n"
        f"Minecraft: <code>{username}</code>\n"
        f"Telegram ID: <code>{telegram_id}</code>\n\n"
        f"{status_text}",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
