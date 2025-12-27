"""
Главный файл для запуска бота
"""
import os
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from dotenv import load_dotenv

from handlers.start import start, verify_callback
from handlers.menu import main_menu_callback, profile_menu
from handlers.politics import politics_menu, my_party, all_parties_handler
from handlers.party_creation import (
    create_party_handler, 
    join_party_by_link
)
from handlers.party_management import (
    party_applications,
    view_application,
    approve_application,
    reject_application,
    party_members_list,
    manage_party_menu,
    show_invite_link,
    leave_party_handler,
    delete_party_handler,
    transfer_leadership_handler
)
from handlers.trade import trade_menu
from handlers.entertainment import entertainment_menu
from handlers.placeholders import placeholder

load_dotenv()


def main():
    """Запуск бота"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN не найден в .env!")
        return
    
    application = Application.builder().token(bot_token).build()
    
    # ========== КОМАНДЫ ==========
    application.add_handler(CommandHandler("start", start))
    
    # ========== CONVERSATION HANDLERS ==========
    application.add_handler(create_party_handler())
    
    # ========== ВЕРИФИКАЦИЯ ==========
    application.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify_"))
    
    # ========== ГЛАВНОЕ МЕНЮ ==========
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(profile_menu, pattern="^profile$"))
    
    # ========== РАЗДЕЛЫ ==========
    application.add_handler(CallbackQueryHandler(politics_menu, pattern="^section_politics$"))
    application.add_handler(CallbackQueryHandler(trade_menu, pattern="^section_trade$"))
    application.add_handler(CallbackQueryHandler(entertainment_menu, pattern="^section_entertainment$"))
    
    # ========== ПОЛИТИКА - ПАРТИИ ==========
    application.add_handler(CallbackQueryHandler(my_party, pattern="^my_party$"))
    application.add_handler(CallbackQueryHandler(all_parties_handler, pattern="^all_parties$"))
    application.add_handler(CallbackQueryHandler(party_applications, pattern="^party_applications_"))
    application.add_handler(CallbackQueryHandler(view_application, pattern="^view_app_"))
    application.add_handler(CallbackQueryHandler(approve_application, pattern="^approve_app_"))
    application.add_handler(CallbackQueryHandler(reject_application, pattern="^reject_app_"))
    application.add_handler(CallbackQueryHandler(party_members_list, pattern="^party_members_"))
    application.add_handler(CallbackQueryHandler(manage_party_menu, pattern="^manage_party_"))
    application.add_handler(CallbackQueryHandler(show_invite_link, pattern="^party_invite_"))
    application.add_handler(CallbackQueryHandler(leave_party_handler, pattern="^leave_party_"))
    application.add_handler(CallbackQueryHandler(delete_party_handler, pattern="^delete_party_"))
    application.add_handler(CallbackQueryHandler(transfer_leadership_handler, pattern="^transfer_leader_"))
    
    # ========== ЗАГЛУШКИ ==========
    application.add_handler(CallbackQueryHandler(placeholder, pattern="^find_party$"))
    application.add_handler(CallbackQueryHandler(placeholder, pattern="^parliament$"))
    application.add_handler(CallbackQueryHandler(placeholder, pattern="^party_list_"))
    
    print("=" * 60)
    print("🤖 БОТ ЗАПУЩЕН!")
    print("=" * 60)
    print("✅ Модули загружены:")
    print("  📝 Верификация")
    print("  🏛️ Политика (Партии)")
    print("  💰 Торговля (заглушка)")
    print("  🎲 Развлечения (заглушка)")
    print("\nНажми Ctrl+C для остановки")
    print("=" * 60)
    
    application.run_polling(allowed_updates=['message', 'callback_query'])


if __name__ == '__main__':
    main()
