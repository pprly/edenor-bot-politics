"""
Фоновые задачи бота
"""
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

from database import db
from utils import auth_checker, send_notification
from config import AUTH_RECHECK_DAYS, PARTY_MIN_MEMBERS

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def check_auth_status(bot: Bot):
    """Проверка статуса авторизации пользователей (раз в месяц)"""
    logger.info("🔍 Запуск проверки авторизации пользователей...")
    
    users = db.get_users_for_auth_recheck(AUTH_RECHECK_DAYS)
    
    for user in users:
        telegram_id = user['telegram_id']
        is_linked, player_data = auth_checker.check_player(telegram_id)
        
        if is_linked:
            db.update_auth_check(telegram_id)
            logger.info(f"✅ Проверка пройдена: {user['minecraft_username']}")
        else:
            db.deactivate_user(telegram_id)
            await send_notification(
                bot, telegram_id,
                "⚠️ <b>Аккаунт отвязан</b>\n\n"
                "Твой Telegram больше не привязан к серверу.\n"
                "Привяжи заново и напиши /start"
            )
            logger.warning(f"❌ Пользователь отвязан: {user['minecraft_username']}")
    
    logger.info(f"✅ Проверка завершена. Проверено: {len(users)}")


async def check_party_deadlines(bot: Bot):
    """Проверка дедлайнов создания партий"""
    logger.info("⏰ Проверка дедлайнов партий...")
    
    # Получаем незарегистрированные партии
    parties = db.get_all_parties(registered_only=False)
    
    for party in parties:
        if party['is_registered']:
            continue
        
        deadline = datetime.fromisoformat(party['registration_deadline'])
        
        if datetime.now() > deadline:
            # Дедлайн истёк
            if party['members_count'] >= PARTY_MIN_MEMBERS:
                # Регистрируем партию
                db.register_party(party['id'])
                members = db.get_party_members(party['id'])
                
                for member in members:
                    await send_notification(
                        bot, member['telegram_id'],
                        f"🎉 <b>Партия зарегистрирована!</b>\n\n"
                        f"Партия <b>{party['name']}</b> набрала {party['members_count']} членов "
                        f"и успешно зарегистрирована!"
                    )
                
                logger.info(f"✅ Партия зарегистрирована: {party['name']}")
            else:
                # Не набрала минимум - удаляем
                members = db.get_party_members(party['id'])
                
                for member in members:
                    await send_notification(
                        bot, member['telegram_id'],
                        f"❌ <b>Партия распущена</b>\n\n"
                        f"Партия <b>{party['name']}</b> не набрала минимум {PARTY_MIN_MEMBERS} членов "
                        f"за отведённое время и была расформирована."
                    )
                
                db.delete_party(party['id'])
                logger.info(f"❌ Партия удалена: {party['name']}")


async def check_voting_deadlines(bot: Bot):
    """Проверка дедлайнов голосований"""
    logger.info("🗳️ Проверка дедлайнов голосований...")
    
    votings = db.get_active_votings()
    
    for voting in votings:
        end_date = datetime.fromisoformat(voting['end_date'])
        
        # Уведомление за час до конца
        if datetime.now() + timedelta(hours=1) >= end_date and datetime.now() < end_date:
            # TODO: Отправить уведомление в канал
            pass
        
        # Закрытие голосования
        if datetime.now() >= end_date:
            db.close_voting(voting['id'])
            logger.info(f"✅ Голосование закрыто: {voting['title']}")


def start_scheduler(bot: Bot):
    """Запуск планировщика"""
    # Проверка авторизации раз в день
    scheduler.add_job(check_auth_status, 'cron', hour=3, args=[bot])
    
    # Проверка дедлайнов партий каждые 5 минут
    scheduler.add_job(check_party_deadlines, 'interval', minutes=5, args=[bot])
    
    # Проверка голосований каждые 10 минут
    scheduler.add_job(check_voting_deadlines, 'interval', minutes=10, args=[bot])
    
    scheduler.start()
    logger.info("📊 Планировщик задач запущен")
