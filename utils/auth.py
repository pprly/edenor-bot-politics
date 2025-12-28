"""
Проверка авторизации через API сервера
"""
import requests
from typing import Optional, Dict, Tuple
import logging

from config import API_URL, API_TOKEN, DEBUG

logger = logging.getLogger(__name__)


class AuthChecker:
    def __init__(self):
        self.api_url = API_URL
        self.token = API_TOKEN
        self.debug = DEBUG
        
        if not self.api_url or not self.token:
            raise ValueError("API_URL и API_TOKEN должны быть указаны в .env файле!")
        
        self.headers = {
            "X-Token": self.token,
            "Content-Type": "application/json"
        }
    
    def check_player(self, telegram_id: int) -> Tuple[bool, Optional[Dict]]:
        """
        Проверяет привязан ли Telegram к игроку на сервере
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            Tuple[bool, Optional[Dict]]: 
                - True если найден, False если нет
                - Данные игрока или None
        """
        data = {
            "authType": "TELEGRAM",
            "value": str(telegram_id)
        }
        
        if self.debug:
            logger.debug(f"Проверяю Telegram ID: {telegram_id}")
            logger.debug(f"URL: {self.api_url}")
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=data,
                timeout=10
            )
            
            if self.debug:
                logger.debug(f"Статус: {response.status_code}")
                logger.debug(f"Ответ: {response.text}")
            
            if response.status_code == 200:
                player_data = response.json()
                logger.info(f"✅ Игрок найден: {player_data.get('username')}")
                return True, player_data
            elif response.status_code == 404:
                logger.info(f"❌ Игрок {telegram_id} не найден в базе")
                return False, None
            else:
                logger.warning(f"⚠️ Неожиданный статус: {response.status_code}")
                return False, None
                
        except requests.exceptions.Timeout:
            logger.error("⏱️ Таймаут запроса к API")
            return False, None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Ошибка запроса: {e}")
            return False, None
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}")
            return False, None


# Глобальный экземпляр
auth_checker = AuthChecker()
