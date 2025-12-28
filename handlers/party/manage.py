"""
Управление партией - полная версия
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, ConversationHandler,
    MessageHandler, CommandHandler, filters
)

from database import db
from utils import require_auth, require_party_leader, notify_party_members
from keyboards import confirm_keyboard, back_button

logger = logging.getLogger(__name__)

# Состояние для редактирования названия
EDIT_NAME = range(1)


@require_auth
async def leave_party_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выход из партии"""
    query = update.callback_query
    await query.answer()
    
    party_id = int(query.data.split('_')[2])
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
    
    party_id = int(query.data.split('_')[2])
    telegram_id = update.effective_user.id
    party = db.get_party_by_id(party_id)
    
    if not party:
        await query.answer("❌ Партия не найдена", show_alert=True)
        return
    
    # Выходим из партии
    success = db.remove_member(telegram_id, party_id)
    
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


@require_party_leader
async def party_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню управления партией"""
    query = update.callback_query
    await query.answer()
    
    party_id = int(query.data.split('_')[2])
    party = db.get_party_by_id(party_id)
    
    if not party:
        await query.answer("❌ Партия не найдена", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Изменить название", callback_data=f"party_edit_name_{party_id}")],
        [InlineKeyboardButton("📋 Редактор списка", callback_data=f"party_edit_list_{party_id}")],
        [InlineKeyboardButton("👑 Передать лидерство", callback_data=f"party_transfer_{party_id}")],
        [InlineKeyboardButton("🗑️ Удалить партию", callback_data=f"party_delete_{party_id}")],
        [InlineKeyboardButton("« Назад", callback_data="party_my")]
    ])
    
    await query.edit_message_text(
        f"⚙️ <b>Управление партией</b>\n\n"
        f"Партия: <b>{party['name']}</b>",
        reply_markup=keyboard,
        parse_mode='HTML'
    )


@require_party_leader
async def delete_party_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления партии"""
    query = update.callback_query
    await query.answer()
    
    party_id = int(query.data.split('_')[2])
    party = db.get_party_by_id(party_id)
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Удалить", callback_data=f"do_delete_party_{party_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"party_manage_{party_id}")
        ]
    ])
    
    await query.edit_message_text(
        f"⚠️ <b>УДАЛЕНИЕ ПАРТИИ</b>\n\n"
        f"Партия: <b>{party['name']}</b>\n"
        f"Членов: {party['members_count']}\n\n"
        f"❗ Это действие НЕОБРАТИМО!\n"
        f"Все члены партии будут исключены.\n\n"
        f"Ты точно хочешь удалить партию?",
        reply_markup=keyboard,
        parse_mode='HTML'
    )


@require_party_leader
async def do_delete_party(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление партии"""
    query = update.callback_query
    await query.answer()
    
    party_id = int(query.data.split('_')[3])
    party = db.get_party_by_id(party_id)
    party_name = party['name']
    
    # Уведомляем всех членов
    await notify_party_members(
        context.bot,
        party_id,
        f"❌ <b>Партия расформирована</b>\n\n"
        f"Партия <b>{party_name}</b> была удалена её главой.",
        exclude_id=update.effective_user.id
    )
    
    # Удаляем партию
    db.delete_party(party_id)
    
    await query.edit_message_text(
        f"✅ <b>Партия удалена</b>\n\n"
        f"Партия <b>{party_name}</b> была расформирована.",
        reply_markup=back_button("menu_politics"),
        parse_mode='HTML'
    )
    
    db.log_action(update.effective_user.id, "Удаление партии", f"Партия: {party_name}")
    logger.info(f"✅ Партия удалена: {party_name}")


@require_party_leader
async def edit_name_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало редактирования названия"""
    query = update.callback_query
    await query.answer()
    
    party_id = int(query.data.split('_')[3])
    context.user_data['edit_party_id'] = party_id
    
    party = db.get_party_by_id(party_id)
    
    await query.edit_message_text(
        f"📝 <b>Изменение названия партии</b>\n\n"
        f"Текущее название: <b>{party['name']}</b>\n\n"
        f"Введи новое название (макс. 50 символов):\n\n"
        f"Используй /cancel для отмены",
        parse_mode='HTML'
    )
    
    return EDIT_NAME


@require_party_leader
async def edit_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение нового названия"""
    new_name = update.message.text.strip()
    
    if len(new_name) > 50:
        await update.message.reply_text(
            "❌ Слишком длинное! Макс. 50 символов.\nПопробуй ещё раз:"
        )
        return EDIT_NAME
    
    party_id = context.user_data.get('edit_party_id')
    if not party_id:
        await update.message.reply_text("❌ Ошибка: партия не найдена")
        return ConversationHandler.END
    
    party = db.get_party_by_id(party_id)
    old_name = party['name']
    
    # Обновляем название
    success = db.update_party_name(party_id, new_name)
    
    if success:
        # Уведомляем членов
        await notify_party_members(
            context.bot,
            party_id,
            f"📝 <b>Партия переименована</b>\n\n"
            f"Старое название: {old_name}\n"
            f"Новое название: <b>{new_name}</b>",
            exclude_id=update.effective_user.id
        )
        
        await update.message.reply_text(
            f"✅ <b>Название изменено!</b>\n\n"
            f"Новое название: <b>{new_name}</b>",
            reply_markup=back_button("party_my"),
            parse_mode='HTML'
        )
        
        db.log_action(update.effective_user.id, "Переименование партии", f"{old_name} → {new_name}")
        logger.info(f"✅ Партия переименована: {old_name} → {new_name}")
    else:
        await update.message.reply_text(
            f"❌ Партия с названием <b>{new_name}</b> уже существует!",
            parse_mode='HTML'
        )
        return EDIT_NAME
    
    return ConversationHandler.END


async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена редактирования"""
    await update.message.reply_text(
        "❌ Редактирование отменено.\nИспользуй /start"
    )
    return ConversationHandler.END


def get_handlers():
    """Возвращает обработчики управления партией"""
    
    edit_name_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_name_start, pattern="^party_edit_name_")],
        states={
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel_edit)],
    )
    
    return [
        CallbackQueryHandler(leave_party_handler, pattern="^party_leave_"),
        CallbackQueryHandler(confirm_leave_party, pattern="^confirm_leave_"),
        CallbackQueryHandler(party_management_menu, pattern="^party_manage_"),
        CallbackQueryHandler(delete_party_confirm, pattern="^party_delete_"),
        CallbackQueryHandler(do_delete_party, pattern="^do_delete_party_"),
        edit_name_conv,
    ]
