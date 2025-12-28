from .common import main_menu_keyboard, back_button, confirm_keyboard
from .party import (
    politics_menu_keyboard, party_management_keyboard, party_edit_keyboard,
    party_member_list_keyboard, party_list_editor_keyboard, application_keyboard,
    ideology_keyboard
)
from .voting import (
    voting_keyboard, election_parties_keyboard, active_votings_keyboard,
    confirm_vote_keyboard, confirm_election_vote_keyboard
)
from .admin import (
    admin_panel_keyboard, admin_voting_type_keyboard, admin_parliament_keyboard,
    admin_stats_keyboard
)

__all__ = [
    'main_menu_keyboard', 'back_button', 'confirm_keyboard',
    'politics_menu_keyboard', 'party_management_keyboard', 'party_edit_keyboard',
    'party_member_list_keyboard', 'party_list_editor_keyboard', 'application_keyboard',
    'ideology_keyboard',
    'voting_keyboard', 'election_parties_keyboard', 'active_votings_keyboard',
    'confirm_vote_keyboard', 'confirm_election_vote_keyboard',
    'admin_panel_keyboard', 'admin_voting_type_keyboard', 'admin_parliament_keyboard',
    'admin_stats_keyboard'
]
