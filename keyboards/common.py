"""
Общие клавиатуры
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard(is_admin: bool = False):
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("🏛️ Политика", callback_data="menu_politics")],
        [InlineKeyboardButton("👤 Профиль", callback_data="menu_profile")],
    ]
    
    if is_admin:
        keyboard.insert(1, [InlineKeyboardButton("⚙️ Админ-панель", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)


def back_button(callback_data: str = "main_menu"):
    """Кнопка назад"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("« Назад", callback_data=callback_data)
    ]])


def confirm_keyboard(confirm_data: str, cancel_data: str):
    """Клавиатура подтверждения"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=confirm_data),
            InlineKeyboardButton("❌ Отмена", callback_data=cancel_data)
        ]
    ])
