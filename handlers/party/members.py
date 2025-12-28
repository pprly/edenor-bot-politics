"""
Управление членами партии
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, ConversationHandler, CommandHandler, filters

from database import db
from utils import require_auth, require_party_leader, send_notification
from keyboards import back_button

logger = logging.getLogger(__name__)

# Состояние для изменения позиции
SET_POSITION = range(1)


@require_party_leader
async def edit_party_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список членов партии - кликабельный"""
    query = update.callback_query
    await query.answer()
    
    party_id = int(query.data.split('_')[3])
    party = db.get_party_by_id(party_id)
    
    if not party:
        await query.answer("❌ Партия не найдена", show_alert=True)
        return
    
    members = db.get_party_members(party_id)
    
    text = f"📋 <b>Управление членами партии {party['name']}</b>\n\n"
    text += "Нажми на участника для действий\n\n"
    
    keyboard = []
    
    for member in members:
        pos = member['list_position']
        name = member['minecraft_username']
        role_icon = "👑" if member['role'] == 'leader' else "👤"
        
        # Все кликабельны
        keyboard.append([
            InlineKeyboardButton(
                f"{pos}. {role_icon} {name}", 
                callback_data=f"member_actions_{party_id}_{member['telegram_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("« Назад", callback_data=f"party_manage_{party_id}")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


@require_party_leader
async def member_actions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню действий с участником"""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    party_id = int(data_parts[2])
    member_id = int(data_parts[3])
    
    party = db.get_party_by_id(party_id)
    member = db.get_user(member_id)
    member_info = db.get_member_info(member_id, party_id)
    
    if not member_info:
        await query.answer("❌ Участник не найден", show_alert=True)
        return
    
    is_leader = member_info['role'] == 'leader'
    
    text = f"👤 <b>{member['minecraft_username']}</b>\n\n"
    text += f"Роль: {'👑 Глава' if is_leader else '👤 Участник'}\n"
    text += f"Позиция в списке: {member_info['list_position']}\n"
    
    keyboard = []
    
    if not is_leader:
        keyboard.append([
            InlineKeyboardButton("🔢 Изменить позицию", callback_data=f"member_setpos_{party_id}_{member_id}")
        ])
        keyboard.append([
            InlineKeyboardButton("👑 Передать лидерство", callback_data=f"member_transfer_{party_id}_{member_id}")
        ])
        keyboard.append([
            InlineKeyboardButton("❌ Исключить", callback_data=f"member_kick_{party_id}_{member_id}")
        ])
    else:
        text += "\n<i>Действия с главой недоступны</i>"
    
    keyboard.append([InlineKeyboardButton("« Назад", callback_data=f"party_edit_list_{party_id}")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


@require_party_leader
async def member_set_position_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало изменения позиции"""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    party_id = int(data_parts[2])
    member_id = int(data_parts[3])
    
    context.user_data['set_position_party_id'] = party_id
    context.user_data['set_position_member_id'] = member_id
    
    member = db.get_user(member_id)
    members = db.get_party_members(party_id)
    
    await query.edit_message_text(
        f"🔢 <b>Изменение позиции</b>\n\n"
        f"Участник: <b>{member['minecraft_username']}</b>\n\n"
        f"Введи новую позицию (от 2 до {len(members)}):\n\n"
        f"<i>Позиция 1 всегда принадлежит главе</i>\n\n"
        f"Используй /cancel для отмены",
        parse_mode='HTML'
    )
    
    return SET_POSITION


async def member_set_position_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение новой позиции"""
    try:
        new_position = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Введи число!")
        return SET_POSITION
    
    party_id = context.user_data.get('set_position_party_id')
    member_id = context.user_data.get('set_position_member_id')
    
    if not party_id or not member_id:
        await update.message.reply_text("❌ Ошибка: данные не найдены")
        return ConversationHandler.END
    
    members = db.get_party_members(party_id)
    
    if new_position < 2 or new_position > len(members):
        await update.message.reply_text(
            f"❌ Позиция должна быть от 2 до {len(members)}!\nПопробуй ещё раз:"
        )
        return SET_POSITION
    
    member = db.get_user(member_id)
    member_info = db.get_member_info(member_id, party_id)
    old_position = member_info['list_position']
    
    if old_position == new_position:
        await update.message.reply_text("❌ Участник уже на этой позиции!")
        return SET_POSITION
    
    # Изменяем позицию
    db.db.execute(
        'UPDATE party_members SET list_position = ? WHERE telegram_id = ? AND party_id = ?',
        (new_position, member_id, party_id)
    )
    
    # Сдвигаем остальных
    if new_position < old_position:
        # Двигаем вверх - сдвигаем тех кто между вниз
        db.db.execute('''
            UPDATE party_members 
            SET list_position = list_position + 1 
            WHERE party_id = ? AND list_position >= ? AND list_position < ? AND telegram_id != ?
        ''', (party_id, new_position, old_position, member_id))
    else:
        # Двигаем вниз - сдвигаем тех кто между вверх
        db.db.execute('''
            UPDATE party_members 
            SET list_position = list_position - 1 
            WHERE party_id = ? AND list_position > ? AND list_position <= ? AND telegram_id != ?
        ''', (party_id, old_position, new_position, member_id))
    
    db.db.commit()
    
    await update.message.reply_text(
        f"✅ <b>Позиция изменена!</b>\n\n"
        f"Участник: <b>{member['minecraft_username']}</b>\n"
        f"Новая позиция: {new_position}",
        reply_markup=back_button("party_my"),
        parse_mode='HTML'
    )
    
    logger.info(f"✅ Позиция изменена: {member['minecraft_username']} {old_position} → {new_position}")
    
    return ConversationHandler.END


@require_party_leader
async def member_kick_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение исключения"""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    party_id = int(data_parts[2])
    member_id = int(data_parts[3])
    
    member = db.get_user(member_id)
    party = db.get_party_by_id(party_id)
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Исключить", callback_data=f"do_kick_{party_id}_{member_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"member_actions_{party_id}_{member_id}")
        ]
    ])
    
    await query.edit_message_text(
        f"⚠️ <b>Подтверди исключение</b>\n\n"
        f"Участник: <b>{member['minecraft_username']}</b>\n"
        f"Партия: <b>{party['name']}</b>\n\n"
        f"Исключить участника из партии?",
        reply_markup=keyboard,
        parse_mode='HTML'
    )


@require_party_leader
async def do_member_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Исключение участника"""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    party_id = int(data_parts[2])
    member_id = int(data_parts[3])
    
    member = db.get_user(member_id)
    party = db.get_party_by_id(party_id)
    
    # Исключаем
    success = db.remove_member(member_id, party_id)
    
    if success:
        # Уведомляем исключённого
        await send_notification(
            context.bot,
            member_id,
            f"❌ <b>Ты исключён из партии</b>\n\n"
            f"Партия: <b>{party['name']}</b>",
            parse_mode='HTML'
        )
        
        await query.edit_message_text(
            f"✅ <b>Участник исключён</b>\n\n"
            f"Участник: <b>{member['minecraft_username']}</b>\n"
            f"Партия: <b>{party['name']}</b>",
            reply_markup=back_button("party_edit_list_" + str(party_id)),
            parse_mode='HTML'
        )
        
        db.log_action(member_id, "Исключён из партии", f"Партия: {party['name']}")
        logger.info(f"✅ Исключён: {member['minecraft_username']} из {party['name']}")
    else:
        await query.answer("❌ Ошибка исключения", show_alert=True)


@require_party_leader
async def member_transfer_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение передачи лидерства"""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    party_id = int(data_parts[2])
    new_leader_id = int(data_parts[3])
    
    party = db.get_party_by_id(party_id)
    new_leader = db.get_user(new_leader_id)
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"do_transfer_{party_id}_{new_leader_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"member_actions_{party_id}_{new_leader_id}")
        ]
    ])
    
    await query.edit_message_text(
        f"⚠️ <b>Подтверди передачу лидерства</b>\n\n"
        f"Партия: <b>{party['name']}</b>\n"
        f"Новый глава: <b>{new_leader['minecraft_username']}</b>\n\n"
        f"После этого ты станешь обычным участником!",
        reply_markup=keyboard,
        parse_mode='HTML'
    )


@require_auth
async def do_transfer_leadership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выполнение передачи лидерства"""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    party_id = int(data_parts[2])
    new_leader_id = int(data_parts[3])
    
    party = db.get_party_by_id(party_id)
    new_leader = db.get_user(new_leader_id)
    old_leader_id = update.effective_user.id
    
    # Передаём лидерство
    db.transfer_leadership(party_id, new_leader_id)
    
    # Уведомляем нового главу
    await send_notification(
        context.bot,
        new_leader_id,
        f"👑 <b>Ты стал главой партии!</b>\n\n"
        f"Партия: <b>{party['name']}</b>\n\n"
        f"Теперь ты можешь управлять партией.",
        parse_mode='HTML'
    )
    
    await query.edit_message_text(
        f"✅ <b>Лидерство передано!</b>\n\n"
        f"Новый глава: <b>{new_leader['minecraft_username']}</b>\n\n"
        f"Теперь ты обычный участник партии.",
        reply_markup=back_button("party_my"),
        parse_mode='HTML'
    )
    
    db.log_action(new_leader_id, "Назначен главой", f"Партия: {party['name']}")
    db.log_action(old_leader_id, "Передал лидерство", f"Партия: {party['name']}")
    logger.info(f"✅ Лидерство передано: {party['name']} → {new_leader['minecraft_username']}")


async def cancel_set_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена изменения позиции"""
    await update.message.reply_text(
        "❌ Отменено. Используй /start"
    )
    return ConversationHandler.END


def get_handlers():
    """Возвращает обработчики управления членами"""
    
    set_position_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(member_set_position_start, pattern="^member_setpos_")],
        states={
            SET_POSITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, member_set_position_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel_set_position)],
    )
    
    return [
        CallbackQueryHandler(edit_party_list, pattern="^party_edit_list_"),
        CallbackQueryHandler(member_actions_menu, pattern="^member_actions_"),
        CallbackQueryHandler(member_kick_confirm, pattern="^member_kick_"),
        CallbackQueryHandler(do_member_kick, pattern="^do_kick_"),
        CallbackQueryHandler(member_transfer_confirm, pattern="^member_transfer_"),
        CallbackQueryHandler(do_transfer_leadership, pattern="^do_transfer_"),
        set_position_conv,
    ]