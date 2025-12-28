"""
Управление партией
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from database import db
from utils import require_auth
from keyboards import confirm_keyboard, back_button

logger = logging.getLogger(__name__)


@require_auth
async def leave_party_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выход из партии"""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем party_id из callback_data
    data_parts = query.data.split('_')
    party_id = int(data_parts[2])  # leave_party_{id}
    
    telegram_id = update.effective_user.id
    party = db.get_party_by_id(party_id)
    
    if not party:
        await query.answer("❌ Партия не найдена", show_alert=True)
        return
    
    # Проверка: глава не может просто выйти
    if party['leader_telegram_id'] == telegram_id:
        await query.edit_message_text(
            "❌ <b>Глава не может выйти из партии</b>\n\n"
            "Сначала:\n"
            "• Передай лидерство другому участнику\n"
            "• Или удали партию полностью\n\n"
            "Используй меню управления партией.",
            reply_markup=back_button("party_my"),
            parse_mode='HTML'
        )
        return
    
    # Подтверждение выхода
    await query.edit_message_text(
        f"⚠️ <b>Подтверди выход из партии</b>\n\n"
        f"Партия: <b>{party['name']}</b>\n\n"
        f"Ты точно хочешь выйти?",
        reply_markup=confirm_keyboard(
            f"confirm_leave_{party_id}",
            "party_my"
        ),
        parse_mode='HTML'
    )


@require_auth
async def confirm_leave_party(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение выхода из партии"""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем party_id
    data_parts = query.data.split('_')
    party_id = int(data_parts[2])  # confirm_leave_{id}
    
    telegram_id = update.effective_user.id
    party = db.get_party_by_id(party_id)
    
    if not party:
        await query.answer("❌ Партия не найдена", show_alert=True)
        return
    
    # Выходим из партии
    success = db.leave_party(telegram_id, party_id)
    
    if success:
        db.log_action(telegram_id, "Выход из партии", f"Партия: {party['name']}")
        
        await query.edit_message_text(
            f"✅ <b>Ты вышел из партии</b>\n\n"
            f"Партия: {party['name']}\n\n"
            f"Теперь ты можешь создать свою партию или вступить в другую.",
            reply_markup=back_button("menu_politics"),
            parse_mode='HTML'
        )
        
        logger.info(f"✅ Пользователь {telegram_id} вышел из партии {party['name']}")
    else:
        await query.answer("❌ Ошибка выхода из партии", show_alert=True)


def get_handlers():
    """Возвращает обработчики управления партией"""
    return [
        CallbackQueryHandler(leave_party_handler, pattern="^leave_party_"),
        CallbackQueryHandler(confirm_leave_party, pattern="^confirm_leave_"),
    ]
