"""
Команды для партий
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from database import db
from utils import require_auth
from keyboards import confirm_keyboard, back_button

logger = logging.getLogger(__name__)


@require_auth
async def party_leave_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /party_leave - выйти из партии"""
    telegram_id = update.effective_user.id
    party = db.get_user_party(telegram_id)
    
    if not party:
        await update.message.reply_text(
            "❌ Ты не состоишь в партии!"
        )
        return
    
    # Проверка: глава не может просто выйти
    if party['leader_telegram_id'] == telegram_id:
        await update.message.reply_text(
            "❌ <b>Глава не может выйти из партии</b>\n\n"
            "Сначала:\n"
            "• Передай лидерство: /party_transfer @username\n"
            "• Или удали партию: /party_delete",
            parse_mode='HTML'
        )
        return
    
    # Подтверждение
    await update.message.reply_text(
        f"⚠️ <b>Подтверди выход</b>\n\n"
        f"Партия: <b>{party['name']}</b>\n\n"
        f"Для подтверждения напиши:\n"
        f"<code>/confirm_leave</code>",
        parse_mode='HTML'
    )


@require_auth
async def confirm_leave_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /confirm_leave - подтвердить выход"""
    telegram_id = update.effective_user.id
    party = db.get_user_party(telegram_id)
    
    if not party:
        await update.message.reply_text("❌ Ты не в партии!")
        return
    
    if party['leader_telegram_id'] == telegram_id:
        await update.message.reply_text("❌ Глава не может выйти!")
        return
    
    # Выходим
    db.remove_member(telegram_id, party['id'])
    db.log_action(telegram_id, "Выход из партии", f"Партия: {party['name']}")
    
    await update.message.reply_text(
        f"✅ <b>Ты вышел из партии</b>\n\n"
        f"Партия: {party['name']}\n\n"
        f"Теперь можешь создать свою партию или вступить в другую.",
        parse_mode='HTML'
    )
    
    logger.info(f"✅ {telegram_id} вышел из {party['name']}")


@require_auth
async def party_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /party_info - информация о партии"""
    telegram_id = update.effective_user.id
    party = db.get_user_party(telegram_id)
    
    if not party:
        await update.message.reply_text("❌ Ты не состоишь в партии!")
        return
    
    status = "✅ Зарегистрирована" if party['is_registered'] else "⏰ Набор членов"
    role = "👑 Глава" if party['leader_telegram_id'] == telegram_id else "👤 Член"
    
    # Список членов
    members = db.get_party_members(party['id'])
    members_text = ""
    for i, member in enumerate(members[:5], 1):
        role_icon = "👑" if member['role'] == 'leader' else "👤"
        members_text += f"{i}. {role_icon} {member['minecraft_username']}\n"
    
    if len(members) > 5:
        members_text += f"... и ещё {len(members) - 5} чел.\n"
    
    await update.message.reply_text(
        f"🏛️ <b>{party['name']}</b>\n\n"
        f"🎯 Идеология: {party['ideology']}\n"
        f"📊 Статус: {status}\n"
        f"👥 Членов: {party['members_count']}\n"
        f"👤 Твоя роль: {role}\n\n"
        f"📋 Описание:\n{party['description']}\n\n"
        f"Члены партии:\n{members_text}\n"
        f"Используй /start для открытия меню",
        parse_mode='HTML'
    )


@require_auth  
async def party_members_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /party_members - список членов"""
    telegram_id = update.effective_user.id
    party = db.get_user_party(telegram_id)
    
    if not party:
        await update.message.reply_text("❌ Ты не в партии!")
        return
    
    members = db.get_party_members(party['id'])
    
    text = f"👥 <b>Члены партии {party['name']}</b>\n\n"
    for i, member in enumerate(members, 1):
        role_icon = "👑" if member['role'] == 'leader' else "👤"
        text += f"{i}. {role_icon} <b>{member['minecraft_username']}</b>\n"
    
    await update.message.reply_text(text, parse_mode='HTML')


def get_handlers():
    """Возвращает обработчики команд партии"""
    return [
        CommandHandler("party_leave", party_leave_command),
        CommandHandler("confirm_leave", confirm_leave_command),
        CommandHandler("party_info", party_info_command),
        CommandHandler("party_members", party_members_command),
    ]
