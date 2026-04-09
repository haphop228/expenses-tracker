import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
API_URL = os.getenv("API_URL", "http://api:8000/api/v1")
BOT_API_TOKEN = os.getenv("BOT_API_TOKEN", "")  # X-Bot-Token для запросов к API

TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")

DEFAULT_CATEGORIES = [
    {"name": "Продукты", "emoji": "🛒"},
    {"name": "Кафе", "emoji": "☕"},
    {"name": "Транспорт", "emoji": "🚕"},
    {"name": "Аптека", "emoji": "💊"},
    {"name": "Досуг", "emoji": "🎮"},
    {"name": "Одежда", "emoji": "👗"},
    {"name": "Дом", "emoji": "🏠"},
    {"name": "Прочее", "emoji": "📦"},
]
