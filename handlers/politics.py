"""
Обработчики раздела Политика
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils.decorators import require_verification
from utils.database import db


@require_verification
async def politics_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню политики"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    
    # Проверяем статус игрока
    user_party = db.get_user_party(telegram_id)
    is_deputy = db.is_deputy(telegram_id)
    
    keyboard = []
    
    if user_party:
        keyboard.append([InlineKeyboardButton("🏛️ Моя партия", callback_data="my_party")])
    else:
        keyboard.append([InlineKeyboardButton("➕ Создать партию", callback_data="create_party")])
        keyboard.append([InlineKeyboardButton("🔍 Найти партию", callback_data="find_party")])
    
    keyboard.append([InlineKeyboardButton("📋 Все партии", callback_data="all_parties")])
    
    if is_deputy:
        keyboard.append([InlineKeyboardButton("⚖️ Парламент", callback_data="parliament")])
    
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    status = ""
    if user_party:
        status = f"Партия: <b>{user_party['name']}</b>\n"
    if is_deputy:
        status += "Статус: <b>Депутат</b>\n"
    
    await query.edit_message_text(
        f"🏛️ <b>ПОЛИТИКА</b>\n\n"
        f"{status}\n"
        f"Управление партиями и парламентом",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


@require_verification
async def my_party(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр своей партии"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    party = db.get_user_party(telegram_id)
    
    if not party:
        await query.answer("❌ Ты не в партии!", show_alert=True)
        return
    
    is_leader = party['leader_telegram_id'] == telegram_id
    
    keyboard = []
    
    if is_leader:
        applications = db.get_party_applications(party['id'])
        if applications:
            keyboard.append([InlineKeyboardButton(
                f"📨 Заявки ({len(applications)})", 
                callback_data=f"party_applications_{party['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            "⚙️ Управление", 
            callback_data=f"manage_party_{party['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        "👥 Список членов", 
        callback_data=f"party_members_{party['id']}"
    )])
    
    keyboard.append([InlineKeyboardButton(
        "🚪 Выйти из партии", 
        callback_data=f"leave_party_{party['id']}"
    )])
    
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="section_politics")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    status = "✅ Зарегистрирована" if party['registered'] else "⏰ Набор членов"
    role = "👑 Глава" if is_leader else "👤 Член"
    
    await query.edit_message_text(
        f"🏛️ <b>{party['name']}</b>\n\n"
        f"Идеология: {party['ideology']}\n"
        f"Статус: {status}\n"
        f"Членов: {party['members_count']}\n"
        f"Твоя роль: {role}\n\n"
        f"📄 Описание:\n{party['description']}",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


@require_verification
async def all_parties_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список всех зарегистрированных партий"""
    query = update.callback_query
    await query.answer()
    
    parties = db.get_all_registered_parties()
    
    if not parties:
        await query.edit_message_text(
            "📋 <b>Зарегистрированные партии</b>\n\n"
            "Пока нет зарегистрированных партий.",
            parse_mode='HTML'
        )
        return
    
    text = "📋 <b>Зарегистрированные партии</b>\n\n"
    
    for i, party in enumerate(parties, 1):
        text += f"{i}. <b>{party['name']}</b>\n"
        text += f"   {party['ideology']}\n"
        text += f"   Членов: {party['members_count']}\n\n"
    
    keyboard = [[InlineKeyboardButton("« Назад", callback_data="section_politics")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
