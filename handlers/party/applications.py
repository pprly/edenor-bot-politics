"""
Обработка заявок на вступление в партию
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from database import db
from utils import require_auth, require_party_leader, send_notification
from keyboards import back_button

logger = logging.getLogger(__name__)


@require_party_leader
async def view_applications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр заявок (только для главы)"""
    query = update.callback_query
    await query.answer()
    
    party_id = int(query.data.split('_')[2])
    party = db.get_party_by_id(party_id)
    
    if not party:
        await query.answer("❌ Партия не найдена", show_alert=True)
        return
    
    applications = db.get_party_applications(party_id, status='pending')
    
    if not applications:
        await query.edit_message_text(
            f"📨 <b>Заявки в партию {party['name']}</b>\n\n"
            f"Нет новых заявок.",
            reply_markup=back_button("party_my"),
            parse_mode='HTML'
        )
        return
    
    text = f"📨 <b>Заявки в партию {party['name']}</b>\n\n"
    text += f"Всего заявок: {len(applications)}\n\n"
    
    keyboard = []
    for app in applications:
        text += f"👤 <b>{app['minecraft_username']}</b>\n"
        keyboard.append([
            InlineKeyboardButton(
                f"✅ {app['minecraft_username']}", 
                callback_data=f"app_approve_{app['id']}"
            ),
            InlineKeyboardButton(
                "❌", 
                callback_data=f"app_reject_{app['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="party_my")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


@require_party_leader
async def approve_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Одобрить заявку"""
    query = update.callback_query
    await query.answer()
    
    app_id = int(query.data.split('_')[2])
    app = db.get_application_by_id(app_id)
    
    if not app:
        await query.answer("❌ Заявка не найдена", show_alert=True)
        return
    
    # Проверяем не в партии ли уже заявитель
    current_party = db.get_user_party(app['telegram_id'])
    if current_party:
        db.reject_application(app_id)
        await query.answer(
            f"❌ {app['minecraft_username']} уже вступил в другую партию",
            show_alert=True
        )
        # Обновляем список заявок
        await view_applications(update, context)
        return
    
    # Одобряем
    success = db.approve_application(app_id)
    
    if success:
        party = db.get_party_by_id(app['party_id'])
        
        # Уведомляем игрока
        await send_notification(
            context.bot,
            app['telegram_id'],
            f"✅ <b>Заявка одобрена!</b>\n\n"
            f"Ты принят в партию <b>{party['name']}</b>!\n"
            f"Добро пожаловать!",
            parse_mode='HTML'
        )
        
        await query.answer(f"✅ {app['minecraft_username']} принят в партию!", show_alert=True)
        
        db.log_action(app['telegram_id'], "Принят в партию", f"Партия: {party['name']}")
        logger.info(f"✅ Заявка одобрена: {app['minecraft_username']} → {party['name']}")
    else:
        await query.answer("❌ Ошибка при одобрении", show_alert=True)
    
    # Обновляем список заявок
    await view_applications(update, context)


@require_party_leader
async def reject_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отклонить заявку"""
    query = update.callback_query
    await query.answer()
    
    app_id = int(query.data.split('_')[2])
    app = db.get_application_by_id(app_id)
    
    if not app:
        await query.answer("❌ Заявка не найдена", show_alert=True)
        return
    
    db.reject_application(app_id)
    
    # Уведомляем игрока
    party = db.get_party_by_id(app['party_id'])
    await send_notification(
        context.bot,
        app['telegram_id'],
        f"❌ <b>Заявка отклонена</b>\n\n"
        f"Твоя заявка в партию <b>{party['name']}</b> была отклонена.",
        parse_mode='HTML'
    )
    
    await query.answer(f"❌ Заявка {app['minecraft_username']} отклонена", show_alert=True)
    
    logger.info(f"❌ Заявка отклонена: {app['minecraft_username']} → {party['name']}")
    
    # Обновляем список заявок
    await view_applications(update, context)


def get_handlers():
    """Возвращает обработчики заявок"""
    return [
        CallbackQueryHandler(view_applications, pattern="^party_applications_"),
        CallbackQueryHandler(approve_application, pattern="^app_approve_"),
        CallbackQueryHandler(reject_application, pattern="^app_reject_"),
    ]
