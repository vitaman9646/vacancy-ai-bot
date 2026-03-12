#!/bin/bash

BACKUP_DIR="/home/botuser/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_PATH="/home/botuser/vacancy-ai-bot/vacancies.db"

mkdir -p $BACKUP_DIR

# Бэкап базы данных
cp $DB_PATH "$BACKUP_DIR/vacancies_$DATE.db"

# Удаление старых бэкапов (старше 30 дней)
find $BACKUP_DIR -name "vacancies_*.db" -mtime +30 -delete

echo "✅ Backup created: vacancies_$DATE.db"
