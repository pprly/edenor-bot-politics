"""
Клавиатуры для голосований
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def voting_keyboard(voting_id: int):
    """Кнопки для голосования"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ За", callback_data=f"vote_{voting_id}_for"),
            InlineKeyboardButton("❌ Против", callback_data=f"vote_{voting_id}_against")
        ]
    ])


def election_parties_keyboard(election_id: int, parties: list, page: int = 0):
    """Список партий для голосования на выборах"""
    keyboard = []
    
    # По 5 партий на странице
    page_size = 5
    start_idx = page * page_size
    end_idx = start_idx + page_size
    
    for i, party in enumerate(parties[start_idx:end_idx], start=start_idx + 1):
        keyboard.append([
            InlineKeyboardButton(
                f"{i}. {party['name']} ({party['ideology']})",
                callback_data=f"election_vote_{election_id}_{party['id']}"
            )
        ])
    
    # Пагинация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"election_parties_{election_id}_page_{page-1}"))
    if end_idx < len(parties):
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"election_parties_{election_id}_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    return InlineKeyboardMarkup(keyboard)


def active_votings_keyboard(votings: list):
    """Список активных голосований"""
    keyboard = []
    
    for voting in votings:
        vote_type_icon = "🏛️" if voting['voting_type'] == 'parliament' else "👥"
        keyboard.append([
            InlineKeyboardButton(
                f"{vote_type_icon} {voting['title'][:30]}...",
                callback_data=f"voting_view_{voting['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)


def confirm_vote_keyboard(voting_id: int, vote_type: str):
    """Подтверждение голоса"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить", callback_data=f"vote_confirm_{voting_id}_{vote_type}")],
        [InlineKeyboardButton("❌ Отмена", callback_data=f"voting_view_{voting_id}")]
    ])


def confirm_election_vote_keyboard(election_id: int, party_id: int):
    """Подтверждение голоса на выборах"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить", callback_data=f"election_confirm_{election_id}_{party_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data=f"election_view_{election_id}")]
    ])
