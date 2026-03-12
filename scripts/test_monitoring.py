#!/usr/bin/env python3
"""Тест мониторинга без запуска полной системы"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.monitor import VacancyMonitor
from src.config import config

async def test_callback(vacancy_data: dict):
    """Тестовый callback"""
    print("\n" + "="*50)
    print(f"📌 {vacancy_data['title']}")
    print(f"💰 {vacancy_data.get('salary', 0)} ₽")
    print(f"🔗 {vacancy_data.get('link', 'нет ссылки')}")
    print(f"📝 {vacancy_data.get('description', '')[:200]}")
    print("="*50 + "\n")

async def main():
    print("🧪 Тестовый мониторинг...")
    print(f"Каналы: {config.channels}")
    print(f"Сайты: {config.site_urls}")
    print("\nНажмите Ctrl+C для остановки\n")
    
    monitor = VacancyMonitor(callback=test_callback)
    
    try:
        # Запускаем на 5 минут для теста
        await asyncio.wait_for(monitor.run(), timeout=300)
    except asyncio.TimeoutError:
        print("\n✅ Тест завершён")
    except KeyboardInterrupt:
        print("\n⏹ Остановлено пользователем")

if __name__ == '__main__':
    asyncio.run(main())
