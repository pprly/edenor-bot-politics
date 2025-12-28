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
CHANNEL_ID = os.getenv('CHANNEL_ID')
REGISTRATION_BOT = os.getenv('REGISTRATION_BOT', '@edenor_bot')

# Admin IDs
ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]

# Database
DATABASE_PATH = os.getenv('DATABASE_PATH', 'politics.db')

# Debug
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Party Settings
PARTY_MIN_MEMBERS = int(os.getenv('PARTY_MIN_MEMBERS', '3'))
PARTY_CREATION_TIME_MINUTES = int(os.getenv('PARTY_CREATION_TIME_MINUTES', '10'))

# Parliament Settings
PARLIAMENT_SEATS = int(os.getenv('PARLIAMENT_SEATS', '40'))
ELECTION_THRESHOLD_PERCENT = int(os.getenv('ELECTION_THRESHOLD_PERCENT', '5'))

# Auth recheck
AUTH_RECHECK_DAYS = int(os.getenv('AUTH_RECHECK_DAYS', '30'))
