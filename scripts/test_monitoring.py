#!/usr/bin/env python3
"""Тестовый запуск мониторинга без полной системы"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.monitor import VacancyMonitor
from src.config import config


async def test_callback(vacancy_data: dict):
    """Тестовый callback для вывода найденных вакансий"""
    
    print("\n" + "=" * 70)
    print(f"📌 {vacancy_data['title']}")
    print("=" * 70)
    print(f"💰 Зарплата: {vacancy_data.get('salary', 0)} ₽")
    print(f"   Мин: {vacancy_data.get('salary_min', '?')} | Макс: {vacancy_data.get('salary_max', '?')}")
    print(f"🔗 Ссылка: {vacancy_data.get('link', 'нет')}")
    print(f"📝 Описание:")
    print(f"   {vacancy_data.get('description', vacancy_data.get('raw_text', ''))[:200]}...")
    print(f"🏢 Компания: {vacancy_data.get('company', 'не указана')}")
    print(f"📍 Локация: {vacancy_data.get('location', 'не указана')}")
    print(f"💼 Тип: {vacancy_data.get('employment_type', 'не указан')}")
    print("=" * 70 + "\n")


async def main():
    print("=" * 70)
    print("🧪 ТЕСТОВЫЙ МОНИТОРИНГ ВАКАНСИЙ")
    print("=" * 70)
    print("")
    print(f"📡 Каналы: {', '.join(config.channels)}")
    print(f"🌐 Сайты: {', '.join(config.site_urls)}")
    print(f"⏱️  Интервал: {config.check_interval} сек")
    print("")
    print("⚠️  Бот будет работать 5 минут для теста")
    print("⌨️  Нажмите Ctrl+C для остановки")
    print("")
    
    monitor = VacancyMonitor(callback=test_callback)
    
    try:
        # Запускаем на 5 минут
        await asyncio.wait_for(monitor.run(), timeout=300)
    except asyncio.TimeoutError:
        print("\n✅ Тест завершён (таймаут 5 минут)")
    except KeyboardInterrupt:
        print("\n⏹️  Остановлено пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")


if __name__ == '__main__':
    asyncio.run(main())
