#!/bin/bash

# Мониторинг ресурсов VPS и здоровья системы

echo "🔍 Проверка системы $(date)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Проверка vacancy-bot
if systemctl is-active --quiet vacancy-bot; then
    echo "✅ vacancy-bot работает"
else
    echo "❌ vacancy-bot НЕ РАБОТАЕТ!"
    echo "🔄 Попытка перезапуска..."
    systemctl restart vacancy-bot
    sleep 5
    if systemctl is-active --quiet vacancy-bot; then
        echo "✅ vacancy-bot успешно перезапущен"
    else
        echo "❌ Не удалось перезапустить vacancy-bot"
    fi
fi

# Проверка n8n (Docker)
if docker ps | grep -q n8n; then
    echo "✅ n8n работает"
else
    echo "❌ n8n НЕ РАБОТАЕТ!"
    echo "🔄 Попытка перезапуска..."
    cd /opt/n8n && docker-compose up -d
fi

# Проверка дискового пространства
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
echo "💾 Использование диска: ${DISK_USAGE}%"

if [ $DISK_USAGE -gt 85 ]; then
    echo "⚠️  ВНИМАНИЕ: Диск заполнен более чем на 85%!"
    # Очистка логов старше 7 дней
    find /home/botuser/vacancy-ai-bot/logs -name "*.log" -mtime +7 -delete
    echo "🗑️  Старые логи удалены"
fi

# Проверка памяти
FREE_MEM=$(free -m | awk 'NR==2 {print $7}')
TOTAL_MEM=$(free -m | awk 'NR==2 {print $2}')
MEM_PERCENT=$((100 - (FREE_MEM * 100 / TOTAL_MEM)))

echo "💾 Использование памяти: ${MEM_PERCENT}% (свободно: ${FREE_MEM}MB)"

if [ $FREE_MEM -lt 200 ]; then
    echo "⚠️  ВНИМАНИЕ: Мало свободной памяти!"
    # Очистка кэша
    sync; echo 3 > /proc/sys/vm/drop_caches 2>/dev/null
    echo "🧹 Кэш очищен"
fi

# Проверка Chrome процессов (могут накапливаться)
CHROME_COUNT=$(ps aux | grep chrome | grep -v grep | wc -l)
echo "🌐 Chrome процессов: $CHROME_COUNT"

if [ $CHROME_COUNT -gt 10 ]; then
    echo "⚠️  Слишком много Chrome процессов!"
    echo "🔄 Перезапуск vacancy-bot для очистки..."
    systemctl restart vacancy-bot
fi

# Проверка логов на ошибки (последние 100 строк)
ERROR_COUNT=$(journalctl -u vacancy-bot -n 100 | grep -i "error\|exception\|critical" | wc -l)
echo "📊 Ошибок в логах (последние 100 строк): $ERROR_COUNT"

if [ $ERROR_COUNT -gt 10 ]; then
    echo "⚠️  Много ошибок в логах! Проверьте: journalctl -u vacancy-bot -n 100"
fi

# Статистика базы данных
if [ -f "/home/botuser/vacancy-ai-bot/vacancies.db" ]; then
    DB_SIZE=$(du -h /home/botuser/vacancy-ai-bot/vacancies.db | cut -f1)
    echo "🗄️  Размер БД: $DB_SIZE"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Проверка завершена"
echo ""
