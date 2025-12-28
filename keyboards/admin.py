"""
Клавиатуры для админ-панели
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def admin_panel_keyboard():
    """Главная панель администратора"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🗳️ Создать голосование", callback_data="admin_create_voting")],
        [InlineKeyboardButton("🏛️ Управление парламентом", callback_data="admin_parliament")],
        [InlineKeyboardButton("📜 Логи действий", callback_data="admin_logs")],
        [InlineKeyboardButton("« Назад", callback_data="main_menu")]
    ])


def admin_voting_type_keyboard():
    """Выбор типа голосования"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏛️ Парламентское", callback_data="admin_voting_parliament")],
        [InlineKeyboardButton("👥 Общее", callback_data="admin_voting_public")],
        [InlineKeyboardButton("« Назад", callback_data="admin_panel")]
    ])


def admin_parliament_keyboard(has_parliament: bool):
    """Управление парламентом"""
    keyboard = []
    
    if has_parliament:
        keyboard.append([InlineKeyboardButton("👥 Просмотр парламента", callback_data="parliament_view")])
        keyboard.append([InlineKeyboardButton("🗳️ Начать новые выборы", callback_data="admin_election_start")])
        keyboard.append([InlineKeyboardButton("❌ Распустить парламент", callback_data="admin_parliament_dissolve")])
    else:
        keyboard.append([InlineKeyboardButton("🗳️ Провести выборы", callback_data="admin_election_start")])
    
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)


def admin_stats_keyboard():
    """Статистика"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("« Назад", callback_data="admin_panel")]
    ])
