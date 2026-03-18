#!/bin/bash

# Скрипт резервного копирования базы данных

BACKUP_DIR="/home/botuser/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_PATH="/home/botuser/vacancy-ai-bot/vacancies.db"

# Создаём директорию для бэкапов
mkdir -p $BACKUP_DIR

# Копируем базу данных
if [ -f "$DB_PATH" ]; then
    cp "$DB_PATH" "$BACKUP_DIR/vacancies_$DATE.db"
    echo "✅ Backup created: vacancies_$DATE.db"
    
    # Удаляем бэкапы старше 30 дней
    find $BACKUP_DIR -name "vacancies_*.db" -mtime +30 -delete
    echo "🗑️  Старые бэкапы удалены (>30 дней)"
    
    # Статистика
    BACKUP_COUNT=$(ls -1 $BACKUP_DIR/vacancies_*.db 2>/dev/null | wc -l)
    BACKUP_SIZE=$(du -sh $BACKUP_DIR | cut -f1)
    echo "📊 Всего бэкапов: $BACKUP_COUNT (размер: $BACKUP_SIZE)"
else
    echo "❌ База данных не найдена: $DB_PATH"
    exit 1
fi
