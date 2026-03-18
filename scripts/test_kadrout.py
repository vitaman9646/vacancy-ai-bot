#!/usr/bin/env python3
"""Тест парсера kadrout.ru"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.parsers.kadrout import KadroutParser


async def main():
    print("=" * 60)
    print("🧪 ТЕСТ ПАРСЕРА KADROUT.RU")
    print("=" * 60)
    print("")
    
    # Создаём парсер (с UI для отладки)
    parser = KadroutParser(headless=False)
    
    try:
        # 1. Тест списка вакансий
        print("1️⃣ Получение списка вакансий...")
        print("")
        
        vacancies = await parser.fetch_vacancies(limit=5)
        
        print(f"✅ Найдено: {len(vacancies)} вакансий\n")
        
        for i, vac in enumerate(vacancies, 1):
            print(f"📌 {i}. {vac.title}")
            print(f"   💰 {vac.salary_min or '?'} - {vac.salary_max or '?'} {vac.salary_currency}")
            print(f"   🔗 {vac.link}")
            print(f"   📝 {vac.raw_text[:100]}...")
            print("")
        
        # 2. Тест детальной страницы
        if vacancies:
            print("\n2️⃣ Получение деталей первой вакансии...")
            print("")
            
            details = await parser.fetch_vacancy_details(vacancies[0].link)
            
            if details:
                print("✅ Детали получены:")
                print(f"   📌 Заголовок: {details.title}")
                print(f"   🏢 Компания: {details.company or 'не указана'}")
                print(f"   📍 Локация: {details.location or 'не указана'}")
                print(f"   💼 Тип: {details.employment_type}")
                print(f"   📝 Описание ({len(details.description)} симв.):")
                print(f"      {details.description[:300]}...")
            else:
                print("❌ Не удалось получить детали")
    
    finally:
        parser._close_driver()
        print("\n" + "=" * 60)
        print("✅ Тест завершён")
        print("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
