"""Мониторинг источников вакансий"""

import asyncio
import hashlib
from datetime import datetime
from typing import Callable, Optional

from src.config import config
from src.database import db
from src.parsers.kadrout import KadroutParser
from src.parsers.base import Vacancy

# Telegram будем импортировать позже если нужен
# from src.parsers.telegram import TelegramParser


class VacancyMonitor:
    """Мониторинг вакансий из разных источников"""
    
    def __init__(self, callback: Callable):
        """
        callback — async функция для обработки новой вакансии
        """
        self.callback = callback
        self.kadrout_parser = KadroutParser(headless=True)
        # self.telegram_parser = TelegramParser()  # Добавим позже
    
    async def run(self):
        """Главный цикл мониторинга"""
        print("✅ Мониторинг запущен")
        
        while True:
            try:
                print(f"🔄 Проверка источников... {datetime.now()}")
                
                # Мониторинг kadrout.ru
                await self.check_kadrout()
                
                # Мониторинг Telegram (если настроен)
                # await self.check_telegram()
                
                await asyncio.sleep(config.check_interval)
            
            except Exception as e:
                print(f"❌ Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(60)
    
    async def check_kadrout(self):
        """Проверка kadrout.ru"""
        try:
            print("🌐 Проверка kadrout.ru...")
            
            # Получаем свежие вакансии
            vacancies = await self.kadrout_parser.fetch_vacancies(limit=30)
            
            print(f"📊 Найдено вакансий: {len(vacancies)}")
            
            for vacancy in vacancies:
                # Генерация хеша для дедупликации
                hash_str = f"{vacancy.title}{vacancy.link}"
                vacancy_hash = hashlib.md5(hash_str.encode()).hexdigest()
                
                # Проверка дубликата
                if db.vacancy_exists(vacancy_hash):
                    continue
                
                # Быстрая фильтрация
                if not self.quick_filter(vacancy):
                    continue
                
                # Получаем детали (опционально — можно сразу отправлять)
                details = await self.kadrout_parser.fetch_vacancy_details(
                    vacancy.link
                )
                
                if details:
                    vacancy = details
                
                # Добавляем hash
                vacancy_data = vacancy.to_dict()
                vacancy_data['hash'] = vacancy_hash
                
                print(f"📩 Новая вакансия: {vacancy.title}")
                
                # Отправляем в пайплайн
                await self.callback(vacancy_data)
        
        except Exception as e:
            print(f"❌ Ошибка мониторинга kadrout: {e}")
    
    def quick_filter(self, vacancy: Vacancy) -> bool:
        """Быстрая фильтрация перед AI-анализом"""
        
        text = f"{vacancy.title} {vacancy.description} {vacancy.raw_text}".lower()
        
        # Обязательные ключевые слова
        has_required = any(
            kw in text 
            for kw in config.required_keywords
        )
        
        if not has_required:
            return False
        
        # Исключения
        has_excluded = any(
            kw in text
            for kw in config.excluded_keywords
        )
        
        if has_excluded:
            return False
        
        # Минимальная зарплата
        if vacancy.salary and vacancy.salary < config.min_profit:
            return False
        
        return True
