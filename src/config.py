"""Конфигурация приложения"""

import os
from dataclasses import dataclass, field
from typing import List, Literal
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

AIProvider = Literal['openrouter', 'groq', 'openai']


@dataclass
class Config:
    """Конфигурация приложения"""
    
    # ============ Telegram ============
    tg_api_id: int = int(os.getenv('TG_API_ID', '0'))
    tg_api_hash: str = os.getenv('TG_API_HASH', '')
    bot_token: str = os.getenv('BOT_TOKEN', '')
    my_chat_id: int = int(os.getenv('MY_CHAT_ID', '0'))
    
    # ============ AI Provider ============
    ai_provider: AIProvider = os.getenv('AI_PROVIDER', 'openrouter')
    
    # OpenRouter
    openrouter_api_key: str = os.getenv('OPENROUTER_API_KEY', '')
    openrouter_model: str = os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3.7-sonnet')
    
    # Groq
    groq_api_key: str = os.getenv('GROQ_API_KEY', '')
    groq_model: str = os.getenv('GROQ_MODEL', 'llama-3.1-70b-versatile')
    
    # OpenAI
    openai_api_key: str = os.getenv('OPENAI_API_KEY', '')
    openai_model: str = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    # ============ n8n ============
    n8n_url: str = os.getenv('N8N_URL', 'http://localhost:5678')
    n8n_api_key: str = os.getenv('N8N_API_KEY', '')
    
    # ============ Бизнес-логика ============
    my_hourly_rate: int = int(os.getenv('MY_HOURLY_RATE', '500'))
    min_profit: int = int(os.getenv('MIN_PROFIT', '30000'))
    max_active_projects: int = int(os.getenv('MAX_ACTIVE_PROJECTS', '10'))
    check_interval: int = int(os.getenv('CHECK_INTERVAL', '600'))
    
    # ============ Мониторинг ============
    channels: List[str] = field(default_factory=lambda: 
        os.getenv('CHANNELS', '@kadrout').split(',')
    )
    site_urls: List[str] = field(default_factory=lambda: 
        os.getenv('SITE_URLS', 'https://kadrout.ru/vacancies').split(',')
    )
    
    # ============ База данных ============
    db_path: str = os.getenv('DB_PATH', 'vacancies.db')
    
    # ============ Логирование ============
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    log_file: str = os.getenv('LOG_FILE', 'logs/bot.log')
    
    # ============ Selenium ============
    selenium_headless: bool = os.getenv('SELENIUM_HEADLESS', 'true').lower() == 'true'
    selenium_timeout: int = int(os.getenv('SELENIUM_TIMEOUT', '30'))
    
    # ============ Фильтры ============
    required_keywords: List[str] = field(default_factory=lambda: [
        'удалённо', 'удаленно', 'remote',
        'python', 'ai', 'smm', 'автоматизация',
        'бот', 'парсинг', 'контент', 'crm',
        'n8n', 'make', 'zapier', 'нейросет',
        'аналитика', 'data', 'машинное обучение'
    ])
    
    excluded_keywords: List[str] = field(default_factory=lambda: [
        'офис москва', 'только офис', 'переезд обязательно',
        'стажёр без оплаты', 'бесплатно', 'волонтёр'
    ])
    
    def get_ai_config(self) -> dict:
        """Получить конфигурацию для текущего AI провайдера"""
        
        if self.ai_provider == 'openrouter':
            return {
                'api_key': self.openrouter_api_key,
                'model': self.openrouter_model,
                'base_url': 'https://openrouter.ai/api/v1',
                'headers': {
                    'HTTP-Referer': 'https://github.com/yourusername/vacancy-ai-bot',
                    'X-Title': 'Vacancy AI Bot'
                }
            }
        
        elif self.ai_provider == 'groq':
            return {
                'api_key': self.groq_api_key,
                'model': self.groq_model,
                'base_url': 'https://api.groq.com/openai/v1'
            }
        
        elif self.ai_provider == 'openai':
            return {
                'api_key': self.openai_api_key,
                'model': self.openai_model,
                'base_url': 'https://api.openai.com/v1'
            }
        
        else:
            raise ValueError(f"Неизвестный AI провайдер: {self.ai_provider}")
    
    def validate(self):
        """Валидация обязательных параметров"""
        
        errors = []
        
        # Telegram
        if not self.tg_api_id or self.tg_api_id == 0:
            errors.append("❌ TG_API_ID не установлен")
        if not self.tg_api_hash:
            errors.append("❌ TG_API_HASH не установлен")
        if not self.bot_token:
            errors.append("❌ BOT_TOKEN не установлен")
        if not self.my_chat_id or self.my_chat_id == 0:
            errors.append("❌ MY_CHAT_ID не установлен")
        
        # AI Provider
        ai_config = self.get_ai_config()
        if not ai_config.get('api_key'):
            errors.append(f"❌ API ключ для {self.ai_provider} не установлен")
        
        if errors:
            raise ValueError(
                "\n⚠️  Ошибки конфигурации:\n" + 
                "\n".join(f"   {e}" for e in errors) +
                "\n\n💡 Заполните .env файл и перезапустите!"
            )
        
        print("✅ Конфигурация валидна")
        print(f"🤖 AI провайдер: {self.ai_provider} ({ai_config['model']})")


# Глобальный экземпляр конфигурации
config = Config()

# Валидация при импорте (можно отключить для тестов)
if __name__ != '__main__':
    try:
        config.validate()
    except ValueError as e:
        print(f"\n{e}\n")
