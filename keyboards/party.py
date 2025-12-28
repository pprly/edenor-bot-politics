"""
Клавиатуры для партий
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def politics_menu_keyboard(has_party: bool, is_deputy: bool):
    """Меню политики"""
    keyboard = []
    
    if has_party:
        keyboard.append([InlineKeyboardButton("🏛️ Моя партия", callback_data="party_my")])
    else:
        keyboard.append([InlineKeyboardButton("➕ Создать партию", callback_data="party_create")])
    
    keyboard.append([InlineKeyboardButton("📋 Все партии", callback_data="party_list")])
    
    if is_deputy or has_party:
        keyboard.append([InlineKeyboardButton("🏛️ Парламент", callback_data="parliament_view")])
    
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)


def party_management_keyboard(party_id: int, is_leader: bool, pending_apps: int = 0):
    """Меню управления партией"""
    keyboard = []
    
    if is_leader and pending_apps > 0:
        keyboard.append([
            InlineKeyboardButton(
                f"📨 Заявки ({pending_apps})", 
                callback_data=f"party_applications_{party_id}"
            )
        ])
    
    if is_leader:
        keyboard.append([InlineKeyboardButton("⚙️ Управление", callback_data=f"party_manage_{party_id}")])
    
    keyboard.append([InlineKeyboardButton("👥 Список членов", callback_data=f"party_members_{party_id}")])
    keyboard.append([InlineKeyboardButton("🚪 Выйти из партии", callback_data=f"party_leave_{party_id}")])
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="menu_politics")])
    
    return InlineKeyboardMarkup(keyboard)


def party_edit_keyboard(party_id: int):
    """Меню редактирования партии"""
    keyboard = [
        [InlineKeyboardButton("📝 Изменить название", callback_data=f"party_edit_name_{party_id}")],
        [InlineKeyboardButton("📋 Редактор списка", callback_data=f"party_edit_list_{party_id}")],
        [InlineKeyboardButton("👑 Передать лидерство", callback_data=f"party_transfer_{party_id}")],
        [InlineKeyboardButton("🗑️ Удалить партию", callback_data=f"party_delete_{party_id}")],
        [InlineKeyboardButton("« Назад", callback_data="party_my")]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def party_member_list_keyboard(party_id: int, members: list, current_page: int = 0, is_leader: bool = False):
    """Список членов партии с возможностью управления"""
    keyboard = []
    
    # Показываем по 5 человек на странице
    page_size = 5
    start_idx = current_page * page_size
    end_idx = start_idx + page_size
    
    for member in members[start_idx:end_idx]:
        role_icon = "👑" if member['role'] == 'leader' else "👤"
        pos = member['list_position']
        name = member['minecraft_username']
        
        button_text = f"{pos}. {role_icon} {name}"
        
        if is_leader and member['role'] != 'leader':
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=f"member_info_{member['telegram_id']}"),
                InlineKeyboardButton("❌", callback_data=f"member_kick_{party_id}_{member['telegram_id']}")
            ])
        else:
            keyboard.append([InlineKeyboardButton(button_text, callback_data="noop")])
    
    # Пагинация
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"party_members_{party_id}_page_{current_page-1}"))
    if end_idx < len(members):
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"party_members_{party_id}_page_{current_page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="party_my")])
    
    return InlineKeyboardMarkup(keyboard)


def party_list_editor_keyboard(party_id: int, members: list):
    """Редактор списка партии (перемещение вверх/вниз)"""
    keyboard = []
    
    for i, member in enumerate(members):
        if member['role'] == 'leader':
            continue
        
        pos = member['list_position']
        name = member['minecraft_username']
        
        buttons = [InlineKeyboardButton(f"{pos}. {name}", callback_data="noop")]
        
        # Кнопка вверх (если не первый)
        if i > 1:  # Пропускаем лидера (0) и первого после него
            buttons.append(InlineKeyboardButton("⬆️", callback_data=f"list_up_{party_id}_{pos}"))
        
        # Кнопка вниз (если не последний)
        if i < len(members) - 1:
            buttons.append(InlineKeyboardButton("⬇️", callback_data=f"list_down_{party_id}_{pos}"))
        
        keyboard.append(buttons)
    
    keyboard.append([InlineKeyboardButton("« Назад", callback_data=f"party_manage_{party_id}")])
    
    return InlineKeyboardMarkup(keyboard)


def application_keyboard(app_id: int, party_id: int):
    """Кнопки для заявки на вступление"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"app_approve_{app_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"app_reject_{app_id}")
        ],
        [InlineKeyboardButton("« Назад", callback_data=f"party_applications_{party_id}")]
    ])


def ideology_keyboard():
    """Выбор идеологии при создании партии"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Милитаризм", callback_data="ideology_militant")],
        [InlineKeyboardButton("💰 Капитализм", callback_data="ideology_capitalist")],
        [InlineKeyboardButton("🌿 Экология", callback_data="ideology_ecology")],
        [InlineKeyboardButton("🏗️ Строительство", callback_data="ideology_builder")],
        [InlineKeyboardButton("🎓 Наука", callback_data="ideology_science")],
        [InlineKeyboardButton("🤝 Центризм", callback_data="ideology_centrist")],
        [InlineKeyboardButton("✏️ Своя идеология", callback_data="ideology_custom")],
    ])
