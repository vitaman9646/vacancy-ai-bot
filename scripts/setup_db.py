#!/usr/bin/env python3
"""Инициализация базы данных"""

import sys
import os

# Добавляем src в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database import db

def main():
    print("🗄️ Инициализация базы данных...")
    
    try:
        db.init_db()
        print("✅ База данных успешно создана!")
        
        # Проверка
        stats = db.get_stats()
        print(f"📊 Статистика: {stats}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
