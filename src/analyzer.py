"""AI-анализ вакансий"""

import json
import httpx
from typing import Dict, Optional

from src.config import config
from src.database import db


# Промпт для AI-анализа
ANALYSIS_PROMPT = """Ты — эксперт-аналитик вакансий для фрилансера-автоматизатора.

ПРОФИЛЬ ФРИЛАНСЕРА:
- Навыки: Python, n8n, Make.com, AI/LLM интеграции, web-scraping, Telegram-боты, SMM-автоматизация
- Ставка: {rate}₽/час
- Инструменты: n8n (self-hosted), Python, Claude/GPT API, Telegram API, Selenium
- Цель: Максимум автоматизации, минимум ручной работы

ВАКАНСИЯ:
Название: {title}
Зарплата: {salary} ₽ (мин: {salary_min}, макс: {salary_max})
Описание: {description}

═══════════════════════════════════════════════════

ВЫПОЛНИ ПОЛНЫЙ АНАЛИЗ:

1. ОПРЕДЕЛИ ТИП ЗАДАЧИ (один из):
   - smm_posting (автопостинг, контент-план, SMM)
   - lead_parsing (парсинг лидов, клиентов с сайтов)
   - content_generation (AI-генерация текстов, картинок, статей)
   - crm_integration (CRM, автоматизация бизнес-процессов)
   - bot_development (Telegram/WhatsApp боты)
   - data_processing (отчёты, аналитика, дашборды)
   - email_outreach (рассылки, follow-up автоматизация)
   - other (опиши что)

2. ПЛАН АВТОМАТИЗАЦИИ (конкретный n8n workflow):
   Опиши ТОЧНО какой workflow построить:
   - Триггер: что запускает процесс?
   - Шаги: конкретные узлы n8n (Schedule, HTTP Request, Code, OpenAI, Telegram, etc.)
   - Внешние API: какие нужны и зачем?
   - Базы данных: что хранить?
   - Сложность: низкая/средняя/высокая
   - Время на создание workflow: сколько часов реально?

3. ФИНАНСОВЫЙ РАСЧЁТ:
   - hours_setup: часы на создание автоматизации
   - hours_monthly_support: часы на поддержку в месяц
   - Затраты = (hours_setup + hours_monthly_support) × {rate}₽
   - extra_costs: доп. затраты (платные API, сервисы) в месяц
   - Профит = зарплата - затраты - extra_costs - 15% (риски + налоги)
   - ROI = (профит / затраты) × 100%

4. СТЕПЕНЬ АВТОМАТИЗАЦИИ:
   - automation_percent: какой % работы можно автоматизировать (0-100)?
   - manual_work: что останется делать вручную?

5. МАСШТАБИРУЕМОСТЬ:
   - scalable: true/false (можно ли переиспользовать для других клиентов?)
   - scale_potential: потенциальный доп. доход от продажи шаблона

6. РЕКОМЕНДАЦИЯ:
   - "Брать" — если профит >{min_profit} и совпадение >70%
   - "Возможно" — если есть нюансы но прибыльно
   - "Пропустить" — иначе

ОТВЕТ СТРОГО В JSON (без markdown, без комментариев):
{{
  "recommendation": "Брать",
  "match_percent": 85,
  "automation_type": "smm_posting",
  "hours_estimate": 20,
  "hours_setup": 4,
  "hours_monthly_support": 3,
  "costs": 13500,
  "extra_costs": 500,
  "profit": 55000,
  "roi": 407,
  "automation_percent": 90,
  "automation_plan": {{
    "title": "Автопостинг в 3 соцсети с AI-генерацией",
    "trigger": "Schedule (каждый день 09:00)",
    "steps": [
      "1. Schedule Trigger → запуск каждый день 09:00",
      "2. Google Sheets → получить контент-план на сегодня",
      "3. OpenAI GPT-4 → сгенерировать текст поста по теме",
      "4. DALL-E → сгенерировать картинку",
      "5. Telegram API → опубликовать в канал",
      "6. VK API → опубликовать в группу",
      "7. Instagram Graph API → опубликовать пост",
      "8. Google Sheets → отметить как опубликовано",
      "9. Telegram → уведомление об успехе/ошибке"
    ],
    "apis_needed": ["OpenAI API", "Telegram Bot API", "VK API", "Instagram Graph API", "Google Sheets API"],
    "databases": ["Google Sheets (контент-план)", "SQLite (логи публикаций)"],
    "n8n_nodes": ["Schedule Trigger", "Google Sheets", "OpenAI", "HTTP Request", "Telegram", "IF", "Code"],
    "complexity": "средняя"
  }},
  "manual_work": "Заполнение контент-плана в Google Sheets 1 раз в неделю (30 минут). Согласование постов с клиентом при необходимости.",
  "scalable": true,
  "scale_potential": "Шаблон можно продать 5-10 другим SMM-клиентам за 15-30k каждому. Потенциальный доход: 75-300k.",
  "risks": [
    "Клиент может часто менять ТЗ и тему постов",
    "Instagram API может ограничить автопостинг",
    "Необходимость модерации контента перед публикацией"
  ],
  "reasoning": "Идеальное совпадение навыков. 90% работы автоматизируется. Высокий ROI. Шаблон переиспользуемый для других клиентов."
}}
"""


class VacancyAnalyzer:
    """AI-анализатор вакансий"""
    
    def __init__(self):
        self.ai_config = config.get_ai_config()
        self.api_key = self.ai_config['api_key']
        self.model = self.ai_config['model']
        self.base_url = self.ai_config['base_url']
        
        # Для OpenRouter нужны дополнительные заголовки
        self.extra_headers = self.ai_config.get('headers', {})
    
    async def analyze(self, vacancy: dict) -> dict:
        """Полный AI-анализ вакансии"""
        
        # Формируем промпт
        prompt = ANALYSIS_PROMPT.format(
            rate=config.my_hourly_rate,
            min_profit=config.min_profit,
            title=vacancy['title'],
            salary=vacancy.get('salary', 'не указана'),
            salary_min=vacancy.get('salary_min', 'не указана'),
            salary_max=vacancy.get('salary_max', 'не указана'),
            description=vacancy.get('description', vacancy.get('raw_text', ''))[:3000]  # Ограничение
        )
        
        # Подготовка запроса
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            **self.extra_headers
        }
        
        payload = {
            'model': self.model,
            'messages': [
                {
                    'role': 'system',
                    'content': 'Ты отвечаешь ТОЛЬКО валидным JSON. Никакого текста до или после JSON.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.3,
            'max_tokens': 3000
        }
        
        # Запрос к AI
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f'{self.base_url}/chat/completions',
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Очистка от возможного markdown
                content = content.strip()
                if content.startswith('```'):
                    content = content.split('\n', 1)[1]
                    content = content.rsplit('```', 1)[0]
                    content = content.replace('json\n', '')
                
                # Парсинг JSON
                analysis = json.loads(content)
                
                # Валидация и корректировка
                analysis = self._validate_analysis(analysis, vacancy)
                
                return analysis
        
        except httpx.HTTPError as e:
            print(f"❌ HTTP ошибка при анализе: {e}")
            raise
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка парсинга JSON от AI: {e}")
            print(f"Ответ AI: {content[:500]}")
            raise
        except Exception as e:
            print(f"❌ Неизвестная ошибка при анализе: {e}")
            raise
    
    def _validate_analysis(self, analysis: dict, vacancy: dict) -> dict:
        """Валидация и корректировка AI-ответа"""
        
        salary = vacancy.get('salary', 0)
        
        # Пересчёт если AI ошибся
        hours_setup = analysis.get('hours_setup', 4)
        hours_support = analysis.get('hours_monthly_support', 2)
        
        # Затраты на работу
        real_costs = (hours_setup + hours_support) * config.my_hourly_rate
        
        # Доп. затраты (API и т.д.)
        extra = analysis.get('extra_costs', 0)
        
        # Профит с учётом рисков (15%)
        real_profit = salary - real_costs - extra
        real_profit = int(real_profit * 0.85)
        
        # ROI
        real_roi = round((real_profit / real_costs * 100) if real_costs > 0 else 0, 1)
        
        # Обновляем значения
        analysis['costs'] = real_costs
        analysis['profit'] = real_profit
        analysis['roi'] = real_roi
        
        # Авто-корректировка рекомендации
        if real_profit < config.min_profit:
            analysis['recommendation'] = 'Пропустить'
            analysis['reasoning'] = f"Низкий профит ({real_profit}₽ < {config.min_profit}₽). " + analysis.get('reasoning', '')
        
        elif analysis.get('automation_percent', 0) < 50:
            if analysis['recommendation'] == 'Брать':
                analysis['recommendation'] = 'Возможно'
                analysis['reasoning'] = f"Низкая автоматизация ({analysis.get('automation_percent')}%). " + analysis.get('reasoning', '')
        
        # Значения по умолчанию
        analysis.setdefault('match_percent', 70)
        analysis.setdefault('automation_type', 'other')
        analysis.setdefault('automation_plan', {})
        analysis.setdefault('manual_work', 'Не определено')
        analysis.setdefault('scalable', False)
        analysis.setdefault('scale_potential', '')
        analysis.setdefault('risks', [])
        
        return analysis


# Глобальный экземпляр
analyzer = VacancyAnalyzer()
