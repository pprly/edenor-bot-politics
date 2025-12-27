"""
Обработчики управления партией
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import verified_users
from utils.decorators import require_verification
from utils.database import db


@require_verification
async def party_applications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр заявок на вступление"""
    query = update.callback_query
    await query.answer()
    
    party_id = int(query.data.split('_')[-1])
    telegram_id = update.effective_user.id
    
    party = db.get_party_by_id(party_id)
    
    # Проверка прав
    if party['leader_telegram_id'] != telegram_id:
        await query.answer("❌ Только глава может смотреть заявки!", show_alert=True)
        return
    
    applications = db.get_party_applications(party_id)
    
    if not applications:
        await query.answer("Нет новых заявок", show_alert=True)
        return
    
    keyboard = []
    for app in applications[:5]:  # Первые 5
        keyboard.append([
            InlineKeyboardButton(
                f"👤 {app['minecraft_username']}", 
                callback_data=f"view_app_{app['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="my_party")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📨 <b>Заявки на вступление</b>\n\n"
        f"Всего заявок: {len(applications)}\n"
        f"Выбери заявку для просмотра:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


@require_verification
async def view_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр конкретной заявки"""
    query = update.callback_query
    await query.answer()
    
    app_id = int(query.data.split('_')[-1])
    app = db.get_application_by_id(app_id)
    
    if not app:
        await query.answer("❌ Заявка не найдена", show_alert=True)
        return
    
    party = db.get_party_by_id(app['party_id'])
    
    # Проверка прав
    if party['leader_telegram_id'] != update.effective_user.id:
        await query.answer("❌ Нет доступа!", show_alert=True)
        return
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_app_{app_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_app_{app_id}")
        ],
        [InlineKeyboardButton("« Назад", callback_data=f"party_applications_{party['id']}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📨 <b>Заявка на вступление</b>\n\n"
        f"Игрок: <b>{app['minecraft_username']}</b>\n"
        f"Telegram ID: <code>{app['telegram_id']}</code>\n"
        f"Дата: {app['applied_at'][:16]}\n\n"
        f"Одобрить или отклонить?",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


@require_verification
async def approve_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Одобрение заявки"""
    query = update.callback_query
    
    app_id = int(query.data.split('_')[-1])
    success = db.approve_application(app_id)
    
    if success:
        await query.answer("✅ Заявка одобрена!", show_alert=True)
        # Возврат к списку
        app = db.get_application_by_id(app_id)
        if app:
            context.user_data['temp'] = {'party_id': app['party_id']}
        await party_applications(update, context)
    else:
        await query.answer("❌ Ошибка одобрения", show_alert=True)


@require_verification
async def reject_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отклонение заявки"""
    query = update.callback_query
    
    app_id = int(query.data.split('_')[-1])
    success = db.reject_application(app_id)
    
    if success:
        await query.answer("❌ Заявка отклонена", show_alert=True)
        await party_applications(update, context)
    else:
        await query.answer("❌ Ошибка", show_alert=True)


@require_verification
async def party_members_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список членов партии"""
    query = update.callback_query
    await query.answer()
    
    party_id = int(query.data.split('_')[-1])
    party = db.get_party_by_id(party_id)
    members = db.get_party_members(party_id)
    
    text = f"👥 <b>Члены партии {party['name']}</b>\n\n"
    
    for i, member in enumerate(members, 1):
        role_icon = "👑" if member['role'] == 'leader' else "👤"
        text += f"{i}. {role_icon} <b>{member['minecraft_username']}</b>\n"
    
    keyboard = [[InlineKeyboardButton("« Назад", callback_data="my_party")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


@require_verification
async def manage_party_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню управления партией"""
    query = update.callback_query
    await query.answer()
    
    party_id = int(query.data.split('_')[-1])
    party = db.get_party_by_id(party_id)
    telegram_id = update.effective_user.id
    
    if party['leader_telegram_id'] != telegram_id:
        await query.answer("❌ Только глава партии!", show_alert=True)
        return
    
    keyboard = [
        [InlineKeyboardButton("🔗 Ссылка-приглашение", callback_data=f"party_invite_{party_id}")],
        [InlineKeyboardButton("👑 Передать лидерство", callback_data=f"transfer_leader_{party_id}")],
        [InlineKeyboardButton("🗑️ Удалить партию", callback_data=f"delete_party_{party_id}")],
        [InlineKeyboardButton("« Назад", callback_data="my_party")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚙️ <b>Управление партией</b>\n\n"
        f"Партия: <b>{party['name']}</b>\n"
        f"Членов: {party['members_count']}\n\n"
        f"Выбери действие:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


@require_verification
async def show_invite_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать ссылку-приглашение"""
    query = update.callback_query
    await query.answer()
    
    party_id = int(query.data.split('_')[-1])
    party = db.get_party_by_id(party_id)
    
    bot_username = context.bot.username
    invite_link = f"https://t.me/{bot_username}?start=join_{party['invite_code']}"
    
    keyboard = [[InlineKeyboardButton("« Назад", callback_data=f"manage_party_{party_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🔗 <b>Ссылка-приглашение</b>\n\n"
        f"<code>{invite_link}</code>\n\n"
        f"Отправь эту ссылку игрокам для вступления в партию.",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


@require_verification
async def leave_party_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выход из партии"""
    query = update.callback_query
    
    party_id = int(query.data.split('_')[-1])
    telegram_id = update.effective_user.id
    party = db.get_party_by_id(party_id)
    
    # Глава не может просто выйти
    if party['leader_telegram_id'] == telegram_id:
        await query.answer(
            "❌ Глава не может выйти! Сначала передай лидерство или удали партию.",
            show_alert=True
        )
        return
    
    success = db.leave_party(telegram_id, party_id)
    
    if success:
        await query.answer("✅ Ты вышел из партии", show_alert=True)
        # Возврат в политику
        from handlers.politics import politics_menu
        await politics_menu(update, context)
    else:
        await query.answer("❌ Ошибка выхода", show_alert=True)


@require_verification
async def delete_party_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление партии"""
    query = update.callback_query
    
    party_id = int(query.data.split('_')[-1])
    telegram_id = update.effective_user.id
    party = db.get_party_by_id(party_id)
    
    if party['leader_telegram_id'] != telegram_id:
        await query.answer("❌ Только глава может удалить партию!", show_alert=True)
        return
    
    success = db.delete_party(party_id)
    
    if success:
        await query.answer("✅ Партия удалена", show_alert=True)
        from handlers.politics import politics_menu
        await politics_menu(update, context)
    else:
        await query.answer("❌ Ошибка удаления", show_alert=True)


@require_verification
async def transfer_leadership_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Передача лидерства"""
    query = update.callback_query
    await query.answer("🚧 Функция в разработке", show_alert=True)
