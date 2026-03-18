"""Telegram-бот для управления системой"""

import asyncio
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.markdown import hbold, hcode, hitalic

from src.config import config
from src.database import db
from src.analyzer import analyzer
from src.builder import builder
from src.monitor import VacancyMonitor


# ═══════════════════════════════════════════════════════════════
#  ИНИЦИАЛИЗАЦИЯ БОТА
# ═══════════════════════════════════════════════════════════════

bot = Bot(token=config.bot_token, parse_mode='HTML')
dp = Dispatcher()


# ═══════════════════════════════════════════════════════════════
#  ПРЕЗЕНТАЦИЯ ВАКАНСИИ
# ═══════════════════════════════════════════════════════════════

async def present_vacancy(vacancy: dict, analysis: dict, vacancy_id: int):
    """Отправка презентации вакансии с кнопками управления"""
    
    plan = analysis.get('automation_plan', {})
    risks = analysis.get('risks', [])
    
    # Эмодзи рекомендации
    rec_emoji = {
        'Брать': '🟢',
        'Возможно': '🟡',
        'Пропустить': '🔴'
    }.get(analysis.get('recommendation', ''), '⚪')
    
    # Прогресс-бар автоматизации
    auto_pct = analysis.get('automation_percent', 0)
    filled = int(auto_pct / 10)
    progress = '█' * filled + '░' * (10 - filled)
    
    # Формирование сообщения
    message = f"""
{rec_emoji} {hbold(analysis.get('recommendation', 'Неизвестно').upper())}

📌 {hbold(vacancy['title'])}
💰 Зарплата: {hbold(str(vacancy.get('salary', '?')))} ₽
{f"   (от {vacancy.get('salary_min', '?')} до {vacancy.get('salary_max', '?')} {vacancy.get('salary_currency', 'RUB')})" if vacancy.get('salary_min') else ""}

━━━━ 💵 ФИНАНСЫ ━━━━
📊 Часы работы: {analysis.get('hours_estimate', '?')} ч
   ├ Настройка: {analysis.get('hours_setup', '?')} ч
   └ Поддержка: {analysis.get('hours_monthly_support', '?')} ч/мес
💸 Затраты: {analysis.get('costs', 0):,} ₽
💰 {hbold(f"ПРОФИТ: {analysis.get('profit', 0):,} ₽")}
📈 ROI: {analysis.get('roi', 0)}%
💳 Доп. расходы: {analysis.get('extra_costs', 0)} ₽/мес

━━━━ 🤖 АВТОМАТИЗАЦИЯ ━━━━
Тип: {hitalic(analysis.get('automation_type', 'unknown'))}
Степень: [{progress}] {auto_pct}%
Совпадение: {analysis.get('match_percent', 0)}%

{hbold('План автоматизации:')}
{plan.get('title', 'Не определён')}

Шаги:
{chr(10).join(plan.get('steps', ['Не определены'])[:5])}
{f"... и ещё {len(plan.get('steps', [])) - 5} шагов" if len(plan.get('steps', [])) > 5 else ""}

🔧 API: {', '.join(plan.get('apis_needed', ['нет'])[:3])}
{f"+ ещё {len(plan.get('apis_needed', [])) - 3}" if len(plan.get('apis_needed', [])) > 3 else ""}
🗄️ БД: {', '.join(plan.get('databases', ['SQLite']))}
👐 Вручную: {analysis.get('manual_work', 'минимум')[:100]}

━━━━ ⚠️ РИСКИ ━━━━
{chr(10).join(f"• {r}" for r in risks[:3])}
{f"• ... и ещё {len(risks) - 3} рисков" if len(risks) > 3 else ""}

━━━━ 📈 МАСШТАБИРОВАНИЕ ━━━━
{"✅ Переиспользуемый шаблон" if analysis.get('scalable') else "❌ Не масштабируется"}
{analysis.get('scale_potential', '')[:150] if analysis.get('scale_potential') else ""}

💡 {hitalic(analysis.get('reasoning', '')[:200])}

🔗 {vacancy.get('link', 'нет ссылки')}
"""
    
    # Кнопки управления
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ БЕРУ В РАБОТУ",
                callback_data=f"take_{vacancy_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 Подробный план",
                callback_data=f"plan_{vacancy_id}"
            ),
            InlineKeyboardButton(
                text="💰 Пересчитать",
                callback_data=f"recalc_{vacancy_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Пропустить",
                callback_data=f"skip_{vacancy_id}"
            )
        ]
    ])
    
    try:
        await bot.send_message(
            config.my_chat_id,
            message,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"❌ Ошибка отправки сообщения: {e}")


# ═══════════════════════════════════════════════════════════════
#  ОБРАБОТЧИКИ КНОПОК
# ═══════════════════════════════════════════════════════════════

@dp.callback_query(F.data.startswith("take_"))
async def handle_take(callback: CallbackQuery):
    """Обработка нажатия 'БЕРУ В РАБОТУ'"""
    
    vacancy_id = int(callback.data.split("_")[1])
    
    # Проверка лимита активных проектов
    active = db.get_active_projects_count()
    
    if active >= config.max_active_projects:
        await callback.answer(
            f"⚠️ У вас уже {active} активных проектов (лимит {config.max_active_projects})",
            show_alert=True
        )
        return
    
    await callback.answer("🚀 Запускаю сборку автоматизации...")
    
    # Обновляем сообщение
    try:
        await callback.message.edit_text(
            callback.message.text + "\n\n⏳ <b>СТАТУС: Собираю workflow...</b>",
            reply_markup=None
        )
    except:
        pass
    
    # Создаём проект
    project_id = db.create_project(vacancy_id)
    
    # Получаем данные вакансии и анализа
    data = db.get_vacancy_with_analysis(vacancy_id)
    
    if not data:
        await bot.send_message(
            config.my_chat_id,
            "❌ Ошибка: данные вакансии не найдены"
        )
        return
    
    # Подготовка данных для builder
    analysis = {
        'automation_type': data['automation_type'],
        'automation_plan': json.loads(data['automation_plan']) if data.get('automation_plan') else {},
        'hours_estimate': data.get('hours_estimate', 0),
        'hours_setup': data.get('hours_setup', 4),
        'hours_monthly_support': data.get('hours_monthly_support', 2),
        'costs': data.get('costs', 0),
        'profit': data.get('profit', 0),
        'manual_work': data.get('manual_work', ''),
    }
    
    vacancy = {
        'title': data['title'],
        'salary': data['salary'],
        'description': data.get('description', ''),
        'link': data['link'],
    }
    
    # ЗАПУСКАЕМ СБОРКУ
    try:
        result = await builder.build(project_id, analysis, vacancy)
        
        # Формируем сообщение о результате
        status_emoji = "✅" if result['status'] == 'created' else "📁"
        
        success_message = f"""
{status_emoji} {hbold('WORKFLOW ГОТОВ!')}

📌 Проект: {vacancy['title'][:50]}
🆔 ID в n8n: {hcode(result.get('n8n_id', 'local'))}
🔗 {result.get('n8n_url', 'файл сохранён локально')}

{result['instructions']}

━━━━━━━━━━━━━━━━━
{hbold('Следующие шаги:')}
1. Свяжись с клиентом и обговори детали
2. Получи API-ключи и доступы
3. Настрой credentials в n8n
4. Протестируй workflow
5. Активируй и мониторь
"""
        
        # Кнопки для работы с workflow
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 Открыть в n8n",
                    url=result.get('n8n_url', config.n8n_url)
                )
            ] if result.get('n8n_url') and result['status'] == 'created' else [],
            [
                InlineKeyboardButton(
                    text="✅ Активировать",
                    callback_data=f"activate_{project_id}"
                ),
                InlineKeyboardButton(
                    text="📝 Заметки",
                    callback_data=f"notes_{project_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="stats"
                )
            ]
        ])
        
        await bot.send_message(
            config.my_chat_id,
            success_message,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
        # Обновляем статистику
        db.update_daily_stats({'projects_taken': 1})
    
    except Exception as e:
        await bot.send_message(
            config.my_chat_id,
            f"❌ Ошибка при сборке workflow:\n{str(e)}\n\n"
            f"Попробуй вручную или напиши /rebuild {project_id}"
        )


@dp.callback_query(F.data.startswith("plan_"))
async def handle_plan(callback: CallbackQuery):
    """Подробный план автоматизации"""
    
    vacancy_id = int(callback.data.split("_")[1])
    data = db.get_vacancy_with_analysis(vacancy_id)
    
    if not data:
        await callback.answer("Данные не найдены", show_alert=True)
        return
    
    plan = json.loads(data['automation_plan']) if data.get('automation_plan') else {}
    
    message = f"""
📋 {hbold('ПОДРОБНЫЙ ПЛАН АВТОМАТИЗАЦИИ')}

🏷️ {data['title']}

{hbold('Тип:')} {data.get('automation_type', 'unknown')}
{hbold('Название:')} {plan.get('title', 'Не определён')}

{hbold('Триггер:')}
{plan.get('trigger', 'Не определён')}

{hbold('Шаги выполнения:')}
{chr(10).join(plan.get('steps', ['Не определены']))}

{hbold('Необходимые API:')}
{chr(10).join(f"• {api}" for api in plan.get('apis_needed', ['нет']))}

{hbold('Узлы n8n:')}
{', '.join(plan.get('n8n_nodes', ['нет']))}

{hbold('Базы данных:')}
{chr(10).join(f"• {d}" for d in plan.get('databases', ['SQLite']))}

{hbold('Сложность:')} {plan.get('complexity', 'неизвестна')}

⏱️ Время на настройку: ~{data.get('hours_setup', 4)} ч
🔧 Поддержка: ~{data.get('hours_monthly_support', 2)} ч/мес

{hbold('Ручная работа:')}
{data.get('manual_work', 'Не определена')}
"""
    
    await callback.message.answer(message)
    await callback.answer()


@dp.callback_query(F.data.startswith("skip_"))
async def handle_skip(callback: CallbackQuery):
    """Пропуск вакансии"""
    
    vacancy_id = int(callback.data.split("_")[1])
    
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE vacancies SET status = 'skipped' WHERE id = ?",
            (vacancy_id,)
        )
    
    try:
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ <b>ПРОПУЩЕНО</b>",
            reply_markup=None
        )
    except:
        pass
    
    await callback.answer("Вакансия пропущена")


@dp.callback_query(F.data.startswith("activate_"))
async def handle_activate(callback: CallbackQuery):
    """Активация workflow в n8n"""
    
    project_id = int(callback.data.split("_")[1])
    
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT n8n_workflow_id FROM projects WHERE id = ?",
            (project_id,)
        ).fetchone()
    
    if not row or row['n8n_workflow_id'] == 'local':
        await callback.answer(
            "Workflow сохранён локально. Импортируй его в n8n вручную.",
            show_alert=True
        )
        return
    
    workflow_id = row['n8n_workflow_id']
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{config.n8n_url}/api/v1/workflows/{workflow_id}",
                headers={
                    'X-N8N-API-KEY': config.n8n_api_key,
                    'Content-Type': 'application/json'
                },
                json={'active': True}
            )
            
            if response.status_code == 200:
                db.update_project(project_id, status='active')
                await callback.answer("✅ Workflow активирован!", show_alert=True)
            else:
                await callback.answer(f"❌ Ошибка: {response.status_code}", show_alert=True)
    
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@dp.callback_query(F.data.startswith("notes_"))
async def handle_notes(callback: CallbackQuery):
    """Добавление заметок к проекту"""
    
    project_id = int(callback.data.split("_")[1])
    
    await callback.message.answer(
        f"📝 Чтобы добавить заметки к проекту #{project_id}, используй команду:\n\n"
        f"/notes {project_id} Текст заметки"
    )
    await callback.answer()


@dp.callback_query(F.data == "stats")
async def handle_stats_button(callback: CallbackQuery):
    """Статистика (из кнопки)"""
    await cmd_stats(callback.message)
    await callback.answer()


@dp.callback_query(F.data.startswith("recalc_"))
async def handle_recalc(callback: CallbackQuery):
    """Пересчёт анализа вакансии"""
    
    vacancy_id = int(callback.data.split("_")[1])
    
    await callback.answer("🔄 Запускаю пересчёт...")
    
    data = db.get_vacancy_with_analysis(vacancy_id)
    
    if not data:
        await callback.message.answer("❌ Данные не найдены")
        return
    
    vacancy_data = {
        'title': data['title'],
        'salary': data['salary'],
        'salary_min': data.get('salary_min'),
        'salary_max': data.get('salary_max'),
        'description': data.get('description', ''),
        'link': data['link']
    }
    
    try:
        # Повторный анализ
        analysis = await analyzer.analyze(vacancy_data)
        
        # Сохраняем
        db.save_analysis(vacancy_id, analysis)
        
        # Отправляем обновлённую презентацию
        await present_vacancy(vacancy_data, analysis, vacancy_id)
        
        await callback.message.answer("✅ Анализ обновлён, смотри новое сообщение выше")
    
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка пересчёта: {e}")


# ═══════════════════════════════════════════════════════════════
#  КОМАНДЫ БОТА
# ═══════════════════════════════════════════════════════════════

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Стартовое сообщение"""
    
    await message.answer(f"""
🤖 {hbold('Vacancy AI Manager')}

Автоматизированная система поиска вакансий с AI-анализом
и автоматической генерацией n8n workflows.

{hbold('Возможности:')}
• 🔍 Мониторинг kadrout.ru 24/7
• 🧠 AI-анализ (Claude Sonnet 4.6)
• 🏗️ Автосборка n8n workflows
• 💰 Расчёт профита и рисков
• 📊 Статистика и аналитика

{hbold('Команды:')}
/stats — статистика и аналитика
/projects — активные проекты
/settings — настройки фильтров
/pause — пауза мониторинга
/resume — возобновить мониторинг
/help — справка

{hbold('AI провайдер:')} {config.ai_provider}
{hbold('Модель:')} {config.get_ai_config()['model']}
""")


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Статистика системы"""
    
    stats = db.get_stats()
    
    await message.answer(f"""
📊 {hbold('СТАТИСТИКА СИСТЕМЫ')}

━━━━ 📈 ОБЩЕЕ ━━━━
🔍 Найдено вакансий: {stats['total_found']}
🏗️ Активных проектов: {stats['active_projects']} / {config.max_active_projects}
✅ Завершено проектов: {stats['completed_projects']}

━━━━ 💰 ФИНАНСЫ ━━━━
💵 Заработано всего: {stats['total_earned']:,} ₽
📈 Средний профит: {int(stats['avg_profit']):,} ₽
📊 Средний ROI: {int(stats['avg_roi'])}%

━━━━ ⚙️ НАСТРОЙКИ ━━━━
💼 Моя ставка: {config.my_hourly_rate} ₽/ч
🎯 Мин. профит: {config.min_profit:,} ₽
🤖 AI: {config.ai_provider} ({config.get_ai_config()['model']})
""")


@dp.message(Command("projects"))
async def cmd_projects(message: types.Message):
    """Список активных проектов"""
    
    with db.get_conn() as conn:
        rows = conn.execute('''
            SELECT 
                p.id, p.status, p.started_at, 
                p.actual_hours, p.actual_income,
                v.title, v.salary
            FROM projects p
            JOIN vacancies v ON p.vacancy_id = v.id
            WHERE p.status IN ('building', 'ready', 'active')
            ORDER BY p.started_at DESC
            LIMIT 20
        ''').fetchall()
    
    if not rows:
        await message.answer("📂 Нет активных проектов")
        return
    
    status_emoji = {
        'building': '🔨',
        'ready': '✅',
        'active': '🟢',
        'completed': '✔️'
    }
    
    text = f"📂 {hbold('АКТИВНЫЕ ПРОЕКТЫ')}\n\n"
    
    for row in rows:
        emoji = status_emoji.get(row['status'], '⚪')
        
        text += (
            f"{emoji} {hbold(row['title'][:40])}\n"
            f"   ID: {row['id']} | Статус: {row['status']}\n"
            f"   ЗП: {row['salary']:,}₽ | Получено: {row['actual_income']:,}₽\n"
            f"   Часов: {row['actual_hours']}\n\n"
        )
    
    await message.answer(text)


@dp.message(Command("settings"))
async def cmd_settings(message: types.Message):
    """Настройки системы"""
    
    await message.answer(f"""
⚙️ {hbold('НАСТРОЙКИ СИСТЕМЫ')}

{hbold('Мониторинг:')}
• Интервал проверки: {config.check_interval // 60} мин
• Каналы: {', '.join(config.channels)}
• Сайты: kadrout.ru

{hbold('Фильтры:')}
• Мин. профит: {config.min_profit:,} ₽
• Макс. проектов: {config.max_active_projects}
• Моя ставка: {config.my_hourly_rate} ₽/ч

{hbold('AI:')}
• Провайдер: {config.ai_provider}
• Модель: {config.get_ai_config()['model']}

{hbold('n8n:')}
• URL: {config.n8n_url}
• API ключ: {'✅ настроен' if config.n8n_api_key else '❌ не настроен'}

💡 Для изменения настроек отредактируй файл .env
""")


@dp.message(Command("pause"))
async def cmd_pause(message: types.Message):
    """Пауза мониторинга (TODO)"""
    await message.answer("⏸️ Команда пока не реализована")


@dp.message(Command("resume"))
async def cmd_resume(message: types.Message):
    """Возобновление мониторинга (TODO)"""
    await message.answer("▶️ Команда пока не реализована")


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Справка"""
    
    await message.answer(f"""
📖 {hbold('СПРАВКА')}

{hbold('Основные команды:')}
/start — информация о боте
/stats — статистика
/projects — активные проекты
/settings — настройки

{hbold('Как работает система:')}

1️⃣ Бот мониторит kadrout.ru каждые {config.check_interval // 60} минут
2️⃣ Новые вакансии фильтруются по ключевым словам
3️⃣ AI анализирует вакансию и создаёт план автоматизации
4️⃣ Тебе приходит презентация с кнопками
5️⃣ Если нажимаешь "БЕРУ" — бот строит n8n workflow
6️⃣ Ты получаешь готовый workflow и инструкции

{hbold('Обратная связь:')}
Если нашёл баг или есть предложения — напиши разработчику
""")


@dp.message(Command("notes"))
async def cmd_notes(message: types.Message):
    """Добавление заметок к проекту"""
    
    try:
        parts = message.text.split(maxsplit=2)
        
        if len(parts) < 3:
            await message.answer(
                "Использование: /notes <project_id> <текст заметки>\n\n"
                "Пример: /notes 5 Клиент оплатил аванс 50%"
            )
            return
        
        project_id = int(parts[1])
        note_text = parts[2]
        
        db.update_project(project_id, client_notes=note_text)
        
        await message.answer(f"✅ Заметка добавлена к проекту #{project_id}")
    
    except ValueError:
        await message.answer("❌ Неверный формат ID проекта")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


# ═══════════════════════════════════════════════════════════════
#  ОБРАБОТКА НОВЫХ ВАКАНСИЙ
# ═══════════════════════════════════════════════════════════════

async def process_new_vacancy(vacancy_data: dict):
    """
    Полный пайплайн обработки новой вакансии
    
    1. Сохранение в БД
    2. AI-анализ
    3. Презентация пользователю
    """
    
    # 1. Сохраняем вакансию
    vacancy_id = db.save_vacancy(vacancy_data)
    
    if not vacancy_id:
        # Дубликат - уже обработана
        return
    
    print(f"📝 Сохранена вакансия #{vacancy_id}: {vacancy_data['title']}")
    
    # 2. AI-анализ
    try:
        print(f"🧠 Запуск AI-анализа...")
        analysis = await analyzer.analyze(vacancy_data)
        
        print(f"✅ Анализ завершён: {analysis['recommendation']}, профит: {analysis['profit']}₽")
    
    except Exception as e:
        print(f"❌ Ошибка AI-анализа: {e}")
        return
    
    # 3. Сохраняем анализ
    db.save_analysis(vacancy_id, analysis)
    
    # Обновляем статистику
    db.update_daily_stats({'vacancies_filtered': 1})
    
    if analysis['recommendation'] in ('Брать', 'Возможно'):
        db.update_daily_stats({'vacancies_recommended': 1})
    
    # 4. Отправляем только если рекомендовано
    if analysis['recommendation'] in ('Брать', 'Возможно'):
        print(f"📤 Отправка презентации пользователю...")
        await present_vacancy(vacancy_data, analysis, vacancy_id)
    else:
        print(f"⏭️ Пропущено: {vacancy_data['title']} (профит: {analysis['profit']}₽)")


# ═══════════════════════════════════════════════════════════════
#  ГЛАВНАЯ ФУНКЦИЯ
# ═══════════════════════════════════════════════════════════════

async def main():
    """Запуск бота и мониторинга"""
    
    print("=" * 60)
    print("🤖 VACANCY AI BOT")
    print("=" * 60)
    print("")
    
    # Валидация конфигурации
    try:
        config.validate()
    except ValueError as e:
        print(e)
        return
    
    # Создание монитора с callback
    monitor = VacancyMonitor(callback=process_new_vacancy)
    
    print("🚀 Запуск системы...")
    print("")
    
    # Запуск бота и монитора параллельно
    await asyncio.gather(
        dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()),
        monitor.run()
    )


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Бот остановлен пользователем")
    except Exception as e:
        print(f"\n\n❌ Критическая ошибка: {e}")
