"""
Проверка авторизации через API сервера
"""
import requests
from typing import Optional, Dict, Tuple

from config import API_URL, API_TOKEN, DEBUG


class MinecraftAuthChecker:
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
            print(f"🔍 Проверяю Telegram ID: {telegram_id}")
            print(f"📡 URL: {self.api_url}")
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=data,
                timeout=10
            )
            
            if self.debug:
                print(f"📊 Статус: {response.status_code}")
                print(f"📄 Ответ: {response.text}")
            
            if response.status_code == 200:
                player_data = response.json()
                if self.debug:
                    print(f"✅ Игрок найден: {player_data}")
                return True, player_data
            elif response.status_code == 404:
                if self.debug:
                    print("❌ Игрок не найден в базе")
                return False, None
            else:
                if self.debug:
                    print(f"⚠️ Неожиданный статус: {response.status_code}")
                return False, None
                
        except requests.exceptions.Timeout:
            print("⏱️ Таймаут запроса к API")
            return False, None
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка запроса: {e}")
            return False, None
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            return False, None


# Глобальный экземпляр
auth_checker = MinecraftAuthChecker()
