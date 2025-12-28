"""
Управление членами партии
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

from database import db
from utils import require_auth, require_party_leader, send_notification
from keyboards import confirm_keyboard, back_button

logger = logging.getLogger(__name__)


@require_party_leader
async def edit_party_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактор списка партии"""
    query = update.callback_query
    await query.answer()
    
    party_id = int(query.data.split('_')[3])
    party = db.get_party_by_id(party_id)
    
    if not party:
        await query.answer("❌ Партия не найдена", show_alert=True)
        return
    
    members = db.get_party_members(party_id)
    
    text = f"📋 <b>Редактор списка партии {party['name']}</b>\n\n"
    text += "Нажми ⬆️ или ⬇️ для изменения позиции\n\n"
    
    keyboard = []
    
    for i, member in enumerate(members):
        pos = member['list_position']
        name = member['minecraft_username']
        role_icon = "👑" if member['role'] == 'leader' else "👤"
        
        buttons = [InlineKeyboardButton(f"{pos}. {role_icon} {name}", callback_data="noop")]
        
        # Лидер всегда первый, его нельзя двигать
        if member['role'] != 'leader':
            # Кнопка вверх (если не сразу после лидера)
            if i > 1:
                buttons.append(InlineKeyboardButton("⬆️", callback_data=f"list_up_{party_id}_{pos}"))
            
            # Кнопка вниз (если не последний)
            if i < len(members) - 1:
                buttons.append(InlineKeyboardButton("⬇️", callback_data=f"list_down_{party_id}_{pos}"))
        
        keyboard.append(buttons)
    
    keyboard.append([InlineKeyboardButton("« Назад", callback_data=f"party_manage_{party_id}")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


@require_party_leader
async def move_member_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переместить участника вверх"""
    query = update.callback_query
    await query.answer("⬆️ Перемещён вверх")
    
    data_parts = query.data.split('_')
    party_id = int(data_parts[2])
    position = int(data_parts[3])
    
    # Меняем местами с предыдущим
    db.swap_member_positions(party_id, position, position - 1)
    
    # Обновляем список
    await edit_party_list(update, context)


@require_party_leader
async def move_member_down(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переместить участника вниз"""
    query = update.callback_query
    await query.answer("⬇️ Перемещён вниз")
    
    data_parts = query.data.split('_')
    party_id = int(data_parts[2])
    position = int(data_parts[3])
    
    # Меняем местами со следующим
    db.swap_member_positions(party_id, position, position + 1)
    
    # Обновляем список
    await edit_party_list(update, context)


@require_party_leader
async def transfer_leadership_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало передачи лидерства"""
    query = update.callback_query
    await query.answer()
    
    party_id = int(query.data.split('_')[2])
    party = db.get_party_by_id(party_id)
    
    members = db.get_party_members(party_id)
    
    # Исключаем текущего главу
    members = [m for m in members if m['role'] != 'leader']
    
    if not members:
        await query.answer("❌ В партии нет других участников!", show_alert=True)
        return
    
    text = f"👑 <b>Передача лидерства</b>\n\n"
    text += f"Партия: <b>{party['name']}</b>\n\n"
    text += "Выбери нового главу:\n\n"
    
    keyboard = []
    for member in members:
        keyboard.append([
            InlineKeyboardButton(
                f"👤 {member['minecraft_username']}",
                callback_data=f"transfer_to_{party_id}_{member['telegram_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("« Отмена", callback_data=f"party_manage_{party_id}")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


@require_party_leader
async def confirm_transfer_leadership(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            InlineKeyboardButton("❌ Отмена", callback_data=f"party_manage_{party_id}")
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


def get_handlers():
    """Возвращает обработчики управления членами"""
    return [
        CallbackQueryHandler(edit_party_list, pattern="^party_edit_list_"),
        CallbackQueryHandler(move_member_up, pattern="^list_up_"),
        CallbackQueryHandler(move_member_down, pattern="^list_down_"),
        CallbackQueryHandler(transfer_leadership_start, pattern="^party_transfer_"),
        CallbackQueryHandler(confirm_transfer_leadership, pattern="^transfer_to_"),
        CallbackQueryHandler(do_transfer_leadership, pattern="^do_transfer_"),
    ]
