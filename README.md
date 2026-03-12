# 🤖 Vacancy AI Bot

Автоматизированная система поиска вакансий, AI-анализа и создания рабочих n8n-автоматизаций.

## 🎯 Возможности

- 🔍 Мониторинг Telegram-каналов и сайтов
- 🧠 AI-анализ вакансий (профит, риски, план автоматизации)
- 🏗️ Автоматическая сборка n8n workflows
- 💬 Telegram-бот для управления
- 📊 Статистика и отчёты

## 🚀 Быстрый старт

```bash
# 1. Клонирование
git clone https://github.com/yourusername/vacancy-ai-bot.git
cd vacancy-ai-bot

# 2. Настройка окружения
cp .env.example .env
nano .env  # Заполни переменные

# 3. Установка
chmod +x setup.sh
./setup.sh

# 4. Запуск
python src/bot.py
