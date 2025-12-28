from .menu import get_handlers as get_menu_handlers
from .profile import get_handlers as get_profile_handlers

def get_handlers():
    """Собирает все обработчики общих разделов"""
    return get_menu_handlers() + get_profile_handlers()
