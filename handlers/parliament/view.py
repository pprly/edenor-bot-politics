"""
Просмотр партий и своей партии
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from database import db
from utils import require_auth
from keyboards import politics_menu_keyboard, party_management_keyboard, back_button

logger = logging.getLogger(__name__)


@require_auth
async def politics_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню политики"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    has_party = db.get_user_party(telegram_id) is not None
    is_deputy = db.is_deputy(telegram_id)
    
    await query.edit_message_text(
        "🏛️ <b>ПОЛИТИКА</b>\n\nУправление партиями и парламентом",
        reply_markup=politics_menu_keyboard(has_party, is_deputy),
        parse_mode='HTML'
    )


@require_auth
async def my_party(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Моя партия"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    party = db.get_user_party(telegram_id)
    
    if not party:
        await query.answer("❌ Ты не в партии!", show_alert=True)
        return
    
    is_leader = party['leader_telegram_id'] == telegram_id
    pending_apps = len(db.get_party_applications(party['id']))
    
    status = "✅ Зарегистрирована" if party['is_registered'] else "⏰ Набор членов"
    role = "👑 Глава" if is_leader else "👤 Член"
    
    await query.edit_message_text(
        f"🏛️ <b>{party['name']}</b>\n\n"
        f"Идеология: {party['ideology']}\n"
        f"Статус: {status}\n"
        f"Членов: {party['members_count']}\n"
        f"Твоя роль: {role}\n\n"
        f"📄 Описание:\n{party['description']}",
        reply_markup=party_management_keyboard(party['id'], is_leader, pending_apps),
        parse_mode='HTML'
    )


@require_auth
async def all_parties(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список всех партий"""
    query = update.callback_query
    await query.answer()
    
    parties = db.get_all_parties(registered_only=True)
    
    if not parties:
        await query.edit_message_text(
            "📋 <b>Зарегистрированные партии</b>\n\nПока нет партий.",
            reply_markup=back_button("menu_politics"),
            parse_mode='HTML'
        )
        return
    
    text = "📋 <b>Зарегистрированные партии</b>\n\n"
    for i, party in enumerate(parties, 1):
        text += f"{i}. <b>{party['name']}</b>\n"
        text += f"   {party['ideology']}\n"
        text += f"   Членов: {party['members_count']}\n\n"
    
    await query.edit_message_text(
        text,
        reply_markup=back_button("menu_politics"),
        parse_mode='HTML'
    )


@require_auth
async def party_members_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список членов партии"""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем party_id из callback_data
    data_parts = query.data.split('_')
    party_id = int(data_parts[2])  # party_members_{id}
    
    party = db.get_party_by_id(party_id)
    
    if not party:
        await query.answer("❌ Партия не найдена", show_alert=True)
        return
    
    members = db.get_party_members(party_id)
    
    if not members:
        await query.edit_message_text(
            f"👥 <b>Члены партии {party['name']}</b>\n\n"
            f"Пока нет членов (это странно, должен быть хотя бы ты!)",
            reply_markup=back_button("party_my"),
            parse_mode='HTML'
        )
        return
    
    text = f"👥 <b>Члены партии {party['name']}</b>\n\n"
    
    for i, member in enumerate(members, 1):
        role_icon = "👑" if member['role'] == 'leader' else "👤"
        text += f"{i}. {role_icon} <b>{member['minecraft_username']}</b>\n"
    
    await query.edit_message_text(
        text,
        reply_markup=back_button("party_my"),
        parse_mode='HTML'
    )


def get_handlers():
    return [
        CallbackQueryHandler(politics_menu, pattern="^menu_politics$"),
        CallbackQueryHandler(my_party, pattern="^party_my$"),
        CallbackQueryHandler(all_parties, pattern="^party_list$"),
        CallbackQueryHandler(party_members_list, pattern="^party_members_"),
    ]
