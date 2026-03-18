"""Мониторинг источников вакансий 24/7"""

import asyncio
import hashlib
from datetime import datetime
from typing import Callable

from src.config import config
from src.database import db
from src.parsers.kadrout import KadroutParser
from src.parsers.base import Vacancy


class VacancyMonitor:
    """Мониторинг вакансий из различных источников"""
    
    def __init__(self, callback: Callable):
        """
        Args:
            callback: Async функция для обработки новой вакансии
        """
        self.callback = callback
        self.kadrout_parser = KadroutParser(headless=config.selenium_headless)
    
    async def run(self):
        """Главный цикл мониторинга"""
        
        print("✅ Мониторинг запущен")
        print(f"⏱️  Интервал проверки: {config.check_interval} секунд")
        print(f"🔍 Источники: kadrout.ru")
        print("")
        
        while True:
            try:
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"🔄 Проверка источников... {now}")
                
                # Мониторинг kadrout.ru
                await self._check_kadrout()
                
                # Обновление статистики
                stats = db.get_stats()
                print(f"📊 Найдено всего: {stats['total_found']} | Активных проектов: {stats['active_projects']}")
                
                # Ожидание до следующей проверки
                print(f"⏳ Следующая проверка через {config.check_interval // 60} минут\n")
                await asyncio.sleep(config.check_interval)
            
            except KeyboardInterrupt:
                print("\n⏹️  Остановка мониторинга...")
                break
            
            except Exception as e:
                print(f"❌ Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(60)
    
    async def _check_kadrout(self):
        """Проверка kadrout.ru"""
        
        try:
            print("🌐 Проверка kadrout.ru...")
            
            # Получаем свежие вакансии
            vacancies = await self.kadrout_parser.fetch_vacancies(limit=30)
            
            print(f"   Найдено вакансий: {len(vacancies)}")
            
            new_count = 0
            filtered_count = 0
            
            for vacancy in vacancies:
                # Генерация хеша для дедупликации
                hash_str = f"{vacancy.title}{vacancy.link}"
                vacancy_hash = hashlib.md5(hash_str.encode()).hexdigest()
                
                # Проверка дубликата
                if db.vacancy_exists(vacancy_hash):
                    continue
                
                new_count += 1
                
                # Быстрая фильтрация
                if not self._quick_filter(vacancy):
                    continue
                
                filtered_count += 1
                
                # Получаем детали (опционально)
                print(f"   📥 Получение деталей: {vacancy.title[:50]}...")
                details = await self.kadrout_parser.fetch_vacancy_details(vacancy.link)
                
                if details:
                    vacancy = details
                
                # Подготовка данных
                vacancy_data = vacancy.to_dict()
                vacancy_data['hash'] = vacancy_hash
                
                print(f"   ✅ Новая вакансия передана в обработку: {vacancy.title}")
                
                # Отправляем в пайплайн (analyzer → bot)
                await self.callback(vacancy_data)
            
            if new_count > 0:
                print(f"   📊 Новых: {new_count}, прошли фильтр: {filtered_count}")
            else:
                print(f"   ℹ️  Новых вакансий не найдено")
            
            # Обновление дневной статистики
            if new_count > 0:
                db.update_daily_stats({
                    'vacancies_found': new_count,
                    'vacancies_filtered': filtered_count
                })
        
        except Exception as e:
            print(f"   ❌ Ошибка мониторинга kadrout: {e}")
    
    def _quick_filter(self, vacancy: Vacancy) -> bool:
        """Быстрая фильтрация перед AI-анализом"""
        
        text = f"{vacancy.title} {vacancy.description} {vacancy.raw_text}".lower()
        
        # Обязательные ключевые слова
        has_required = any(kw in text for kw in config.required_keywords)
        
        if not has_required:
            return False
        
        # Исключения
        has_excluded = any(kw in text for kw in config.excluded_keywords)
        
        if has_excluded:
            return False
        
        # Минимальная зарплата
        if vacancy.salary > 0 and vacancy.salary < (config.min_profit // 2):
            return False
        
        return True

"""Мониторинг источников вакансий 24/7"""

import asyncio
import hashlib
from datetime import datetime
from typing import Callable

from src.config import config
from src.database import db
from src.parsers.kadrout import KadroutParser
from src.parsers.telegram import telegram_parser  # Новое
from src.parsers.base import Vacancy


class VacancyMonitor:
    """Мониторинг вакансий из различных источников"""
    
    def __init__(self, callback: Callable):
        """
        Args:
            callback: Async функция для обработки новой вакансии
        """
        self.callback = callback
        self.kadrout_parser = KadroutParser(headless=config.selenium_headless)
        self.telegram_parser = telegram_parser  # Новое
        self.use_telegram = len(config.channels) > 0  # Новое
    
    async def run(self):
        """Главный цикл мониторинга"""
        
        print("✅ Мониторинг запущен")
        print(f"⏱️  Интервал проверки: {config.check_interval} секунд")
        
        sources = []
        if config.site_urls:
            sources.append("kadrout.ru")
        if self.use_telegram:
            sources.append(f"Telegram ({', '.join(config.channels)})")
        
        print(f"🔍 Источники: {', '.join(sources)}")
        print("")
        
        # Подключаемся к Telegram если нужно
        if self.use_telegram:
            try:
                await self.telegram_parser.start()
            except Exception as e:
                print(f"⚠️ Не удалось подключиться к Telegram: {e}")
                self.use_telegram = False
        
        while True:
            try:
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"🔄 Проверка источников... {now}")
                
                # Мониторинг kadrout.ru
                if config.site_urls:
                    await self._check_kadrout()
                
                # Мониторинг Telegram (НОВОЕ)
                if self.use_telegram:
                    await self._check_telegram()
                
                # Статистика
                stats = db.get_stats()
                print(f"📊 Найдено всего: {stats['total_found']} | Активных проектов: {stats['active_projects']}")
                
                # Ожидание
                print(f"⏳ Следующая проверка через {config.check_interval // 60} минут\n")
                await asyncio.sleep(config.check_interval)
            
            except KeyboardInterrupt:
                print("\n⏹️  Остановка мониторинга...")
                if self.use_telegram:
                    await self.telegram_parser.stop()
                break
            
            except Exception as e:
                print(f"❌ Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(60)
    
    async def _check_kadrout(self):
        """Проверка kadrout.ru"""
        
        try:
            print("🌐 Проверка kadrout.ru...")
            
            vacancies = await self.kadrout_parser.fetch_vacancies(limit=30)
            
            print(f"   Найдено вакансий: {len(vacancies)}")
            
            new_count = 0
            filtered_count = 0
            
            for vacancy in vacancies:
                hash_str = f"{vacancy.title}{vacancy.link}"
                vacancy_hash = hashlib.md5(hash_str.encode()).hexdigest()
                
                if db.vacancy_exists(vacancy_hash):
                    continue
                
                new_count += 1
                
                if not self._quick_filter(vacancy):
                    continue
                
                filtered_count += 1
                
                print(f"   📥 Получение деталей: {vacancy.title[:50]}...")
                details = await self.kadrout_parser.fetch_vacancy_details(vacancy.link)
                
                if details:
                    vacancy = details
                
                vacancy_data = vacancy.to_dict()
                vacancy_data['hash'] = vacancy_hash
                
                print(f"   ✅ Новая вакансия передана в обработку: {vacancy.title}")
                
                await self.callback(vacancy_data)
            
            if new_count > 0:
                print(f"   📊 Новых: {new_count}, прошли фильтр: {filtered_count}")
            else:
                print(f"   ℹ️  Новых вакансий не найдено")
            
            if new_count > 0:
                db.update_daily_stats({
                    'vacancies_found': new_count,
                    'vacancies_filtered': filtered_count
                })
        
        except Exception as e:
            print(f"   ❌ Ошибка мониторинга kadrout: {e}")
    
    async def _check_telegram(self):
        """Проверка Telegram каналов (НОВОЕ)"""
        
        try:
            print("📱 Проверка Telegram каналов...")
            
            vacancies = await self.telegram_parser.fetch_vacancies(limit=50)
            
            print(f"   Найдено сообщений-вакансий: {len(vacancies)}")
            
            new_count = 0
            filtered_count = 0
            
            for vacancy in vacancies:
                hash_str = f"{vacancy.title}{vacancy.link}"
                vacancy_hash = hashlib.md5(hash_str.encode()).hexdigest()
                
                if db.vacancy_exists(vacancy_hash):
                    continue
                
                new_count += 1
                
                if not self._quick_filter(vacancy):
                    continue
                
                filtered_count += 1
                
                vacancy_data = vacancy.to_dict()
                vacancy_data['hash'] = vacancy_hash
                
                print(f"   ✅ Новая вакансия из Telegram: {vacancy.title}")
                
                await self.callback(vacancy_data)
            
            if new_count > 0:
                print(f"   📊 Новых: {new_count}, прошли фильтр: {filtered_count}")
            else:
                print(f"   ℹ️  Новых вакансий не найдено")
            
            if new_count > 0:
                db.update_daily_stats({
                    'vacancies_found': new_count,
                    'vacancies_filtered': filtered_count
                })
        
        except Exception as e:
            print(f"   ❌ Ошибка мониторинга Telegram: {e}")
    
    def _quick_filter(self, vacancy: Vacancy) -> bool:
        """Быстрая фильтрация перед AI-анализом"""
        
        text = f"{vacancy.title} {vacancy.description} {vacancy.raw_text}".lower()
        
        has_required = any(kw in text for kw in config.required_keywords)
        
        if not has_required:
            return False
        
        has_excluded = any(kw in text for kw in config.excluded_keywords)
        
        if has_excluded:
            return False
        
        if vacancy.salary > 0 and vacancy.salary < (config.min_profit // 2):
            return False
        
        return True
