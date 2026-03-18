#!/usr/bin/env python3
"""Инициализация базы данных"""

import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database import db


def main():
    print("=" * 60)
    print("🗄️  ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ")
    print("=" * 60)
    print("")
    
    try:
        # БД уже инициализируется при импорте
        print("✅ База данных инициализирована")
        print(f"📁 Путь: {db.db_path}")
        
        # Проверка таблиц
        with db.get_conn() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            
            print(f"\n📊 Созданные таблицы ({len(tables)}):")
            for table in tables:
                print(f"   • {table['name']}")
        
        # Статистика
        stats = db.get_stats()
        print(f"\n📈 Статистика:")
        print(f"   • Вакансий: {stats['total_found']}")
        print(f"   • Проектов: {stats['active_projects']}")
        print("")
        print("✅ Готово!")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
