# src/config.py

import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

# Загрузка .env
load_dotenv()

@dataclass
class Config:
    # Telegram
    tg_api_id: int = int(os.getenv('TG_API_ID', '0'))
    tg_api_hash: str = os.getenv('TG_API_HASH', '')
    bot_token: str = os.getenv('BOT_TOKEN', '')
    my_chat_id: int = int(os.getenv('MY_CHAT_ID', '0'))

    # AI
    groq_api_key: str = os.getenv('GROQ_API_KEY', '')
    ai_model: str = os.getenv('AI_MODEL', 'llama-3.1-70b-versatile')

    # n8n
    n8n_url: str = os.getenv('N8N_URL', 'http://localhost:5678')
    n8n_api_key: str = os.getenv('N8N_API_KEY', '')

    # Настройки
    my_hourly_rate: int = int(os.getenv('MY_HOURLY_RATE', '500'))
    min_profit: int = int(os.getenv('MIN_PROFIT', '30000'))
    max_active_projects: int = int(os.getenv('MAX_ACTIVE_PROJECTS', '10'))
    check_interval: int = int(os.getenv('CHECK_INTERVAL', '600'))

    # Мониторинг
    channels: List[str] = field(default_factory=lambda: 
        os.getenv('CHANNELS', '@kadrout').split(',')
    )
    site_urls: List[str] = field(default_factory=lambda: 
        os.getenv('SITE_URLS', 'https://kadrout.ru/vacancies').split(',')
    )

    # База данных
    db_path: str = os.getenv('DB_PATH', 'vacancies.db')

    # Логирование
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')

    # Фильтры
    required_keywords: List[str] = field(default_factory=lambda: [
        'удалённо', 'удаленно', 'remote',
        'python', 'ai', 'smm', 'автоматизация',
        'бот', 'парсинг', 'контент', 'crm',
        'n8n', 'make', 'zapier', 'нейросет'
    ])

    excluded_keywords: List[str] = field(default_factory=lambda: [
        'офис', 'москва обязательно', 'full-time офис',
        'переезд', 'стажёр', 'без оплаты'
    ])

    def validate(self):
        """Проверка обязательных параметров"""
        errors = []
        
        if not self.tg_api_id or self.tg_api_id == 0:
            errors.append("TG_API_ID не установлен")
        if not self.tg_api_hash:
            errors.append("TG_API_HASH не установлен")
        if not self.bot_token:
            errors.append("BOT_TOKEN не установлен")
        if not self.my_chat_id or self.my_chat_id == 0:
            errors.append("MY_CHAT_ID не установлен")
        if not self.groq_api_key:
            errors.append("GROQ_API_KEY не установлен")
        
        if errors:
            raise ValueError(
                "Ошибки конфигурации:\n" + "\n".join(f"- {e}" for e in errors)
            )

config = Config()

# Валидация при импорте
try:
    config.validate()
except ValueError as e:
    print(f"⚠️  {e}")
    print("\nЗаполните .env файл и перезапустите!")
