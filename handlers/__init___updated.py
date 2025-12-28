"""
Сборка всех обработчиков
"""
from handlers.start import get_handler as get_start_handler
from handlers.common import get_handlers as get_common_handlers
from handlers.party.create import get_handler as get_party_create_handler
from handlers.party.view import get_handlers as get_party_view_handlers
from handlers.party.manage import get_handlers as get_party_manage_handlers
from handlers.party.commands import get_handlers as get_party_commands_handlers
from handlers.admin.panel import get_handlers as get_admin_handlers


def get_all_handlers():
    """Собрать все обработчики бота"""
    handlers = []
    
    # Команда /start (должна быть первой)
    handlers.append(get_start_handler())
    
    # Создание партии (ConversationHandler)
    handlers.append(get_party_create_handler())
    
    # Общие обработчики
    handlers.extend(get_common_handlers())
    
    # Партии
    handlers.extend(get_party_view_handlers())
    handlers.extend(get_party_manage_handlers())
    handlers.extend(get_party_commands_handlers())
    
    # Админка
    handlers.extend(get_admin_handlers())
    
    return handlers
