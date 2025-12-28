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
        # Получаем главу
        leader = db.get_user(party['leader_telegram_id'])
        leader_name = leader['minecraft_username'] if leader else "???"
        
        text += f"{i}. <b>{party['name']}</b> • {party['ideology']}\n"
        text += f"   👑 {leader_name} • "
        text += f"👥 <a href='https://t.me/{context.bot.username}?start=party_{party['id']}'>{party['members_count']} участников</a>\n\n"
    
    text += "\n<i>Нажми на участников для просмотра состава</i>"
    
    await query.edit_message_text(
        text,
        reply_markup=back_button("menu_politics"),
        parse_mode='HTML',
        disable_web_page_preview=True
    )


@require_auth
async def party_members_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список членов партии"""
    query = update.callback_query
    await query.answer()
    
    party_id = int(query.data.split('_')[2])
    party = db.get_party_by_id(party_id)
    
    if not party:
        await query.answer("❌ Партия не найдена", show_alert=True)
        return
    
    members = db.get_party_members(party_id)
    telegram_id = update.effective_user.id
    is_leader = party['leader_telegram_id'] == telegram_id
    
    text = f"👥 <b>Члены партии {party['name']}</b>\n\n"
    for member in members:
        role_icon = "👑" if member['role'] == 'leader' else "👤"
        pos = member['list_position']
        text += f"{pos}. {role_icon} <b>{member['minecraft_username']}</b>\n"
    
    # Кнопки
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = []
    
    if is_leader:
        keyboard.append([InlineKeyboardButton("⚙️ Редактировать список", callback_data=f"party_edit_list_{party_id}")])
    
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="party_my")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )


async def handle_party_deeplink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка deep link для просмотра партии"""
    args = context.args
    if not args or not args[0].startswith('party_'):
        return
    
    party_id = int(args[0].replace('party_', ''))
    telegram_id = update.effective_user.id
    
    # Проверяем авторизацию
    user = db.get_user(telegram_id)
    if not user:
        from utils import auth_checker
        from config import REGISTRATION_BOT
        
        is_linked, player_data = auth_checker.check_player(telegram_id)
        if not is_linked:
            await update.message.reply_text(
                f"❌ Сначала пройди верификацию!\n\n"
                f"1. Привяжи Telegram через {REGISTRATION_BOT}\n"
                f"2. Напиши /start"
            )
            return
        
        # Добавляем пользователя
        minecraft_username = player_data.get('username')
        db.add_user(telegram_id, minecraft_username)
    
    # Показываем партию
    party = db.get_party_by_id(party_id)
    
    if not party:
        await update.message.reply_text("❌ Партия не найдена")
        return
    
    members = db.get_party_members(party_id)
    leader = db.get_user(party['leader_telegram_id'])
    
    text = f"🏛️ <b>{party['name']}</b>\n\n"
    text += f"🎯 Идеология: {party['ideology']}\n"
    text += f"👑 Глава: {leader['minecraft_username']}\n"
    text += f"👥 Членов: {party['members_count']}\n\n"
    text += f"📋 <b>Описание:</b>\n{party['description']}\n\n"
    text += f"<b>Список членов:</b>\n"
    
    for member in members:
        role_icon = "👑" if member['role'] == 'leader' else "👤"
        text += f"{member['list_position']}. {role_icon} {member['minecraft_username']}\n"
    
    # Кнопка "Назад в меню"
    from keyboards import main_menu_keyboard
    from config import ADMIN_IDS
    is_admin = telegram_id in ADMIN_IDS
    
    await update.message.reply_text(
        text, 
        parse_mode='HTML',
        reply_markup=main_menu_keyboard(is_admin)
    )


async def show_party_info(update, context, party_id):
    """Показать информацию о партии (для команды)"""
    party = db.get_party_by_id(party_id)
    
    if not party:
        await update.message.reply_text("❌ Партия не найдена")
        return
    
    members = db.get_party_members(party_id)
    leader = db.get_user(party['leader_telegram_id'])
    
    text = f"🏛️ <b>{party['name']}</b>\n\n"
    text += f"🎯 Идеология: {party['ideology']}\n"
    text += f"👑 Глава: {leader['minecraft_username']}\n"
    text += f"👥 Членов: {party['members_count']}\n\n"
    text += f"📋 <b>Описание:</b>\n{party['description']}\n\n"
    text += f"<b>Список членов:</b>\n"
    
    for member in members:
        role_icon = "👑" if member['role'] == 'leader' else "👤"
        text += f"{member['list_position']}. {role_icon} {member['minecraft_username']}\n"
    
    await update.message.reply_text(text, parse_mode='HTML')


@require_auth
async def party_info_by_name_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /party_info <название> - просмотр партии"""
    
    if not context.args:
        # Если без аргументов - показываем свою партию
        telegram_id = update.effective_user.id
        party = db.get_user_party(telegram_id)
        
        if not party:
            await update.message.reply_text("❌ Ты не в партии!\n\nИспользуй: /party_info <название>")
            return
        
        await show_party_info(update, context, party['id'])
        return
    
    # Ищем партию по названию
    party_name = ' '.join(context.args)
    
    cursor = db.db.execute(
        'SELECT id FROM parties WHERE name = ? COLLATE NOCASE AND is_registered = 1',
        (party_name,)
    )
    party = cursor.fetchone()
    
    if not party:
        await update.message.reply_text(
            f"❌ <b>Партия не найдена</b>\n\n"
            f"Партия <code>{party_name}</code> не существует.\n\n"
            f"Используй /start → Политика → Все партии для просмотра списка",
            parse_mode='HTML'
        )
        return
    
    await show_party_info(update, context, party[0])


def get_handlers():
    from telegram.ext import CommandHandler
    return [
        CallbackQueryHandler(politics_menu, pattern="^menu_politics$"),
        CallbackQueryHandler(my_party, pattern="^party_my$"),
        CallbackQueryHandler(all_parties, pattern="^party_list$"),
        CallbackQueryHandler(party_members_list, pattern="^party_members_"),
        CommandHandler("party_info", party_info_by_name_command),
    ]