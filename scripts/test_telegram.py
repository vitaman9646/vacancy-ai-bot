#!/usr/bin/env python3
"""Тест Telegram парсера"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.parsers.telegram import telegram_parser
from src.config import config


async def main():
    print("=" * 70)
    print("🧪 ТЕСТ TELEGRAM ПАРСЕРА")
    print("=" * 70)
    print("")
    
    # Тест подключения
    print("1️⃣ Проверка подключения к Telegram...")
    
    connected = await telegram_parser.test_connection()
    
    if not connected:
        print("\n❌ Не удалось подключиться к Telegram")
        print("Проверь TG_API_ID и TG_API_HASH в .env")
        return
    
    print("")
    
    # Информация о каналах
    print("2️⃣ Информация о каналах:")
    print("")
    
    for channel in config.channels:
        info = await telegram_parser.get_channel_info(channel)
        print(f"📡 {channel}")
        print(f"   Название: {info['title']}")
        print(f"   Подписчиков: {info.get('participants_count', 'N/A')}")
        print(f"   Описание: {info.get('description', 'нет')[:100]}")
        print("")
    
    # Получение вакансий
    print("3️⃣ Получение последних вакансий...")
    print("")
    
    vacancies = await telegram_parser.fetch_vacancies(limit=10)
    
    print(f"✅ Найдено: {len(vacancies)} вакансий\n")
    
    for i, vac in enumerate(vacancies, 1):
        print(f"📌 {i}. {vac.title}")
        print(f"   💰 {vac.salary_min or '?'} - {vac.salary_max or '?'} {vac.salary_currency}")
        print(f"   🔗 {vac.link}")
        print(f"   📝 {vac.raw_text[:100]}...")
        print(f"   📍 Тип: {vac.employment_type}")
        print(f"   🏢 Компания: {vac.company or 'не указана'}")
        print("")
    
    # Остановка
    await telegram_parser.stop()
    
    print("=" * 70)
    print("✅ Тест завершён")
    print("=" * 70)


if __name__ == '__main__':
    asyncio.run(main())
