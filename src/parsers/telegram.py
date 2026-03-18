"""Парсер Telegram-каналов через Telethon"""

import re
import asyncio
from typing import List, Optional
from telethon import TelegramClient
from telethon.tl.types import Message

from .base import BaseParser, Vacancy
from src.config import config


class TelegramParser(BaseParser):
    """Парсер Telegram-каналов с вакансиями"""
    
    def __init__(self):
        """Инициализация Telethon клиента"""
        self.client = TelegramClient(
            'vacancy_bot_session',
            config.tg_api_id,
            config.tg_api_hash
        )
        self.last_message_ids = {}  # Словарь {channel: last_id}
    
    async def start(self):
        """Запуск клиента"""
        if not self.client.is_connected():
            await self.client.start()
            print("✅ Telegram клиент подключен")
    
    async def stop(self):
        """Остановка клиента"""
        if self.client.is_connected():
            await self.client.disconnect()
            print("⏹️ Telegram клиент отключен")
    
    async def fetch_vacancies(self, limit: int = 20) -> List[Vacancy]:
        """
        Получить новые вакансии из всех каналов
        
        Args:
            limit: Максимум сообщений из каждого канала
            
        Returns:
            Список вакансий
        """
        await self.start()
        
        all_vacancies = []
        
        for channel in config.channels:
            try:
                vacancies = await self._fetch_from_channel(channel, limit)
                all_vacancies.extend(vacancies)
            except Exception as e:
                print(f"❌ Ошибка парсинга канала {channel}: {e}")
                continue
        
        return all_vacancies
    
    async def _fetch_from_channel(self, channel: str, limit: int) -> List[Vacancy]:
        """Получить вакансии из конкретного канала"""
        
        vacancies = []
        
        # Получаем последний обработанный ID
        last_id = self.last_message_ids.get(channel, 0)
        
        try:
            # Получаем новые сообщения
            async for message in self.client.iter_messages(
                channel,
                limit=limit,
                min_id=last_id
            ):
                # Пропускаем не текстовые сообщения
                if not message.text:
                    continue
                
                # Быстрая проверка на вакансию
                if not self._is_vacancy(message.text):
                    continue
                
                # Парсим вакансию
                vacancy = self._parse_message(message, channel)
                
                if vacancy:
                    vacancies.append(vacancy)
                
                # Обновляем last_id
                if message.id > last_id:
                    self.last_message_ids[channel] = message.id
        
        except Exception as e:
            print(f"❌ Ошибка чтения канала {channel}: {e}")
        
        return vacancies
    
    def _is_vacancy(self, text: str) -> bool:
        """
        Быстрая проверка - похоже ли сообщение на вакансию
        
        Args:
            text: Текст сообщения
            
        Returns:
            True если похоже на вакансию
        """
        text_lower = text.lower()
        
        # Ключевые слова вакансий
        vacancy_keywords = [
            'вакансия', 'vacancy',
            'ищем', 'требуется', 'нужен', 'нужна',
            'работа', 'job',
            'hiring', 'работу',
            'зарплата', 'оплата', 'salary',
            '₽', 'руб', 'рублей'
        ]
        
        # Исключения (не вакансии)
        excluded_keywords = [
            'резюме ищу работу',
            'ищу удаленную работу',
            'в поисках работы',
            'рассмотрю предложения'
        ]
        
        # Проверка исключений
        for excluded in excluded_keywords:
            if excluded in text_lower:
                return False
        
        # Проверка ключевых слов
        return any(keyword in text_lower for keyword in vacancy_keywords)
    
    def _parse_message(self, message: Message, channel: str) -> Optional[Vacancy]:
        """
        Парсинг сообщения в объект Vacancy
        
        Args:
            message: Telethon Message объект
            channel: Название канала
            
        Returns:
            Объект Vacancy или None
        """
        text = message.text
        
        # Извлечение данных
        title = self._extract_title(text)
        salary_data = self._extract_salary(text)
        link = self._extract_link(message)
        description = text
        employment_type = self._extract_employment_type(text)
        company = self._extract_company(text)
        
        return Vacancy(
            title=title,
            link=link,
            salary_min=salary_data['min'],
            salary_max=salary_data['max'],
            salary_currency=salary_data['currency'],
            description=description,
            raw_text=text,
            source=f'telegram:{channel}',
            company=company,
            employment_type=employment_type
        )
    
    def _extract_title(self, text: str) -> str:
        """
        Извлечение заголовка вакансии
        
        Обычно это первая строка или после "Вакансия:"
        """
        lines = text.split('\n')
        
        # Ищем строку с "Вакансия:" или "Vacancy:"
        for line in lines:
            if re.search(r'вакансия[:\s]', line, re.I):
                title = re.sub(r'вакансия[:\s]*', '', line, flags=re.I)
                return title.strip()[:100]
        
        # Если нет - берём первую непустую строку
        for line in lines:
            if line.strip() and len(line.strip()) > 5:
                return line.strip()[:100]
        
        return 'Вакансия без названия'
    
    def _extract_salary(self, text: str) -> dict:
        """
        Извлечение зарплаты
        
        Форматы:
        - "80000 руб"
        - "от 50000"
        - "50000-80000"
        - "50-80к"
        - "$1000"
        """
        text = text.replace(' ', '').replace('\xa0', '')
        
        # Определение валюты
        currency = 'RUB'
        if '$' in text or 'usd' in text.lower() or 'dollar' in text.lower():
            currency = 'USD'
        elif '€' in text or 'eur' in text.lower():
            currency = 'EUR'
        
        patterns = [
            # Диапазон: "50000-80000" или "50-80"
            r'(\d+)\s*[-–—]\s*(\d+)\s*(?:к|k|тыс|000)?',
            
            # "От X до Y"
            r'(?:от|from)\s*(\d+)\s*(?:до|to|-)\s*(\d+)\s*(?:к|k|тыс|000)?',
            
            # "От X"
            r'(?:от|from|зп)\s*(\d+)\s*(?:к|k|тыс|000)?',
            
            # "До X"
            r'(?:до|to|up\s*to)\s*(\d+)\s*(?:к|k|тыс|000)?',
            
            # Просто число с валютой
            r'(\d+)\s*(?:₽|руб|rub|к|k)',
            
            # Просто большое число (>10000)
            r'(\d{5,})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = [g for g in match.groups() if g]
                
                if len(groups) >= 2:
                    # Диапазон
                    min_val = int(groups[0])
                    max_val = int(groups[1])
                    
                    # Обработка "к" (тысячи)
                    if 'к' in match.group(0).lower() or 'k' in match.group(0).lower():
                        if min_val < 1000:
                            min_val *= 1000
                        if max_val < 1000:
                            max_val *= 1000
                    
                    return {'min': min_val, 'max': max_val, 'currency': currency}
                
                elif len(groups) == 1:
                    # Одно значение
                    val = int(groups[0])
                    
                    # Обработка "к"
                    if 'к' in match.group(0).lower() or 'k' in match.group(0).lower():
                        if val < 1000:
                            val *= 1000
                    
                    # Если в тексте "от" - это минимум
                    if re.search(r'(?:от|from)', text[:match.start()], re.I):
                        return {'min': val, 'max': None, 'currency': currency}
                    # Если "до" - это максимум
                    elif re.search(r'(?:до|to)', text[:match.start()], re.I):
                        return {'min': None, 'max': val, 'currency': currency}
                    else:
                        # Иначе - точное значение
                        return {'min': val, 'max': val, 'currency': currency}
        
        return {'min': None, 'max': None, 'currency': currency}
    
    def _extract_link(self, message: Message) -> str:
        """
        Извлечение ссылки из сообщения
        
        Приоритет:
        1. Entities (кнопки, ссылки)
        2. Текстовые ссылки в сообщении
        3. Ссылка на само сообщение
        """
        # 1. Проверяем entities (встроенные ссылки/кнопки)
        if message.entities:
            for entity in message.entities:
                if hasattr(entity, 'url') and entity.url:
                    return entity.url
        
        # 2. Ищем текстовые ссылки
        urls = re.findall(
            r'https?://[^\s<>"{}|\\^`\[\]]+',
            message.text or ''
        )
        if urls:
            return urls[0]
        
        # 3. Ссылка на само сообщение в канале
        if message.peer_id:
            try:
                channel_username = message.peer_id.channel_id
                return f'https://t.me/c/{channel_username}/{message.id}'
            except:
                pass
        
        return f'https://t.me/{message.chat.username}/{message.id}' if message.chat and message.chat.username else ''
    
    def _extract_employment_type(self, text: str) -> str:
        """Определение типа занятости"""
        text_lower = text.lower()
        
        if any(kw in text_lower for kw in ['удалённо', 'удаленно', 'remote', 'remotely']):
            return 'remote'
        elif any(kw in text_lower for kw in ['офис', 'office', 'on-site']):
            return 'office'
        elif any(kw in text_lower for kw in ['гибрид', 'hybrid']):
            return 'hybrid'
        
        return 'unknown'
    
    def _extract_company(self, text: str) -> str:
        """Извлечение названия компании"""
        
        # Паттерны для поиска компании
        patterns = [
            r'компания[:\s]+([^\n]+)',
            r'employer[:\s]+([^\n]+)',
            r'организация[:\s]+([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return match.group(1).strip()[:50]
        
        return ''
    
    async def fetch_vacancy_details(self, url: str) -> Optional[Vacancy]:
        """
        Получить детали вакансии по ссылке
        
        Для Telegram это не применимо - вся информация уже в сообщении
        """
        return None
    
    async def get_channel_info(self, channel: str) -> dict:
        """
        Получить информацию о канале
        
        Args:
            channel: Название канала (например: @kadrout)
            
        Returns:
            Словарь с информацией о канале
        """
        await self.start()
        
        try:
            entity = await self.client.get_entity(channel)
            
            return {
                'title': entity.title if hasattr(entity, 'title') else channel,
                'username': entity.username if hasattr(entity, 'username') else channel,
                'participants_count': entity.participants_count if hasattr(entity, 'participants_count') else None,
                'description': entity.about if hasattr(entity, 'about') else '',
            }
        except Exception as e:
            print(f"❌ Не удалось получить информацию о {channel}: {e}")
            return {'title': channel, 'username': channel}
    
    async def test_connection(self) -> bool:
        """
        Тест подключения к Telegram
        
        Returns:
            True если подключение успешно
        """
        try:
            await self.start()
            
            # Пробуем получить информацию о себе
            me = await self.client.get_me()
            print(f"✅ Подключен как: {me.first_name} (@{me.username})")
            
            return True
        
        except Exception as e:
            print(f"❌ Ошибка подключения к Telegram: {e}")
            return False


# Глобальный экземпляр
telegram_parser = TelegramParser()
