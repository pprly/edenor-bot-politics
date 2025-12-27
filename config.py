"""
Конфигурация бота
"""
import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
API_URL = os.getenv('API_URL')
API_TOKEN = os.getenv('API_TOKEN')

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
REGISTRATION_BOT = os.getenv('REGISTRATION_BOT', '@edenor_bot')

# Database
DATABASE_PATH = os.getenv('DATABASE_PATH', 'politics.db')

# Debug
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Хранилище верифицированных пользователей (в памяти)
verified_users = {}
