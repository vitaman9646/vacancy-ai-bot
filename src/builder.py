"""Автоматическая сборка n8n workflows"""

import json
import os
import httpx
from typing import Dict, Optional

from src.config import config
from src.database import db


# ═══════════════════════════════════════════════════════════════
#  ШАБЛОНЫ N8N WORKFLOWS
# ═══════════════════════════════════════════════════════════════

WORKFLOW_TEMPLATES = {
    
    "smm_posting": {
        "name": "SMM Auto-Posting — {client}",
        "nodes": [
            {
                "name": "Daily Schedule",
                "type": "n8n-nodes-base.scheduleTrigger",
                "parameters": {
                    "rule": {
                        "interval": [{"field": "hours", "hoursInterval": 24}]
                    }
                },
                "position": [250, 300],
                "typeVersion": 1
            },
            {
                "name": "Get Content Plan",
                "type": "n8n-nodes-base.googleSheets",
                "parameters": {
                    "operation": "read",
                    "sheetName": "ContentPlan",
                    "options": {}
                },
                "position": [450, 300],
                "typeVersion": 3,
                "credentials": {
                    "googleSheetsOAuth2Api": "{НАСТРОЙ_GOOGLE_SHEETS}"
                }
            },
            {
                "name": "Filter Today",
                "type": "n8n-nodes-base.code",
                "parameters": {
                    "jsCode": "const today = new Date().toISOString().split('T')[0];\nreturn $input.all().filter(item => \n    item.json.date === today && item.json.status !== 'posted'\n);"
                },
                "position": [650, 300],
                "typeVersion": 2
            },
            {
                "name": "Generate Post Text",
                "type": "@n8n/n8n-nodes-langchain.openAi",
                "parameters": {
                    "model": "gpt-4o-mini",
                    "messages": {
                        "values": [
                            {
                                "content": "Ты SMM-менеджер для {business_type}. Напиши пост на тему: {{$json.topic}}. Стиль: {tone}. Длина: {length} слов. Добавь эмодзи и хэштеги."
                            }
                        ]
                    }
                },
                "position": [850, 300],
                "typeVersion": 1,
                "credentials": {
                    "openAiApi": "{НАСТРОЙ_OPENAI}"
                }
            },
            {
                "name": "Post to Telegram",
                "type": "n8n-nodes-base.telegram",
                "parameters": {
                    "operation": "sendMessage",
                    "chatId": "{ЗАПОЛНИ_ID_КАНАЛА_КЛИЕНТА}",
                    "text": "={{$json.generated_text}}"
                },
                "position": [1050, 200],
                "typeVersion": 1,
                "credentials": {
                    "telegramApi": "{НАСТРОЙ_TELEGRAM}"
                }
            },
            {
                "name": "Mark as Posted",
                "type": "n8n-nodes-base.googleSheets",
                "parameters": {
                    "operation": "update",
                    "sheetName": "ContentPlan"
                },
                "position": [1250, 300],
                "typeVersion": 3
            },
            {
                "name": "Notify Me",
                "type": "n8n-nodes-base.telegram",
                "parameters": {
                    "operation": "sendMessage",
                    "chatId": "{my_chat_id}",
                    "text": "✅ Опубликовано для {client}: {{$json.topic}}"
                },
                "position": [1250, 450],
                "typeVersion": 1
            }
        ],
        "connections": {
            "Daily Schedule": {"main": [[{"node": "Get Content Plan", "type": "main", "index": 0}]]},
            "Get Content Plan": {"main": [[{"node": "Filter Today", "type": "main", "index": 0}]]},
            "Filter Today": {"main": [[{"node": "Generate Post Text", "type": "main", "index": 0}]]},
            "Generate Post Text": {"main": [[{"node": "Post to Telegram", "type": "main", "index": 0}]]},
            "Post to Telegram": {"main": [[{"node": "Mark as Posted", "type": "main", "index": 0}]]},
            "Mark as Posted": {"main": [[{"node": "Notify Me", "type": "main", "index": 0}]]}
        }
    },
    
    "lead_parsing": {
        "name": "Lead Parser — {client}",
        "nodes": [
            {
                "name": "Schedule Every 6h",
                "type": "n8n-nodes-base.scheduleTrigger",
                "parameters": {
                    "rule": {
                        "interval": [{"field": "hours", "hoursInterval": 6}]
                    }
                },
                "position": [250, 300],
                "typeVersion": 1
            },
            {
                "name": "Scrape Source",
                "type": "n8n-nodes-base.httpRequest",
                "parameters": {
                    "url": "{source_url}",
                    "method": "GET",
                    "options": {}
                },
                "position": [450, 300],
                "typeVersion": 4
            },
            {
                "name": "Parse HTML",
                "type": "n8n-nodes-base.code",
                "parameters": {
                    "jsCode": "// Парсинг HTML\nconst cheerio = require('cheerio');\nconst $ = cheerio.load($json.data);\nconst leads = [];\n\n$('{selector}').each((i, el) => {\n    leads.push({\n        name: $(el).find('.name').text(),\n        contact: $(el).find('.contact').text(),\n        details: $(el).find('.details').text()\n    });\n});\n\nreturn leads.map(l => ({json: l}));"
                },
                "position": [650, 300],
                "typeVersion": 2
            },
            {
                "name": "AI Qualify Lead",
                "type": "@n8n/n8n-nodes-langchain.openAi",
                "parameters": {
                    "model": "gpt-4o-mini",
                    "messages": {
                        "values": [
                            {
                                "content": "Оцени качество лида для {business_type}:\nИмя: {{$json.name}}\nДетали: {{$json.details}}\n\nОтвет в JSON: {\"quality\": \"hot/warm/cold\", \"reason\": \"причина\"}"
                            }
                        ]
                    }
                },
                "position": [850, 300],
                "typeVersion": 1
            },
            {
                "name": "Filter Hot Leads",
                "type": "n8n-nodes-base.if",
                "parameters": {
                    "conditions": {
                        "string": [
                            {
                                "value1": "={{$json.quality}}",
                                "value2": "hot"
                            }
                        ]
                    }
                },
                "position": [1050, 300],
                "typeVersion": 1
            },
            {
                "name": "Save to Notion",
                "type": "n8n-nodes-base.notion",
                "parameters": {
                    "operation": "create",
                    "resource": "databasePage",
                    "databaseId": "{ЗАПОЛНИ_NOTION_DB_ID}"
                },
                "position": [1250, 200],
                "typeVersion": 1,
                "credentials": {
                    "notionApi": "{НАСТРОЙ_NOTION}"
                }
            },
            {
                "name": "Notify Client",
                "type": "n8n-nodes-base.telegram",
                "parameters": {
                    "operation": "sendMessage",
                    "chatId": "{ЗАПОЛНИ_CLIENT_CHAT_ID}",
                    "text": "🔥 Новый горячий лид:\n{{$json.name}}\n{{$json.reason}}"
                },
                "position": [1250, 400],
                "typeVersion": 1
            }
        ],
        "connections": {
            "Schedule Every 6h": {"main": [[{"node": "Scrape Source", "type": "main", "index": 0}]]},
            "Scrape Source": {"main": [[{"node": "Parse HTML", "type": "main", "index": 0}]]},
            "Parse HTML": {"main": [[{"node": "AI Qualify Lead", "type": "main", "index": 0}]]},
            "AI Qualify Lead": {"main": [[{"node": "Filter Hot Leads", "type": "main", "index": 0}]]},
            "Filter Hot Leads": {
                "main": [
                    [
                        {"node": "Save to Notion", "type": "main", "index": 0},
                        {"node": "Notify Client", "type": "main", "index": 0}
                    ]
                ]
            }
        }
    },
    
    "content_generation": {
        "name": "Content Generator — {client}",
        "nodes": [
            {
                "name": "Daily Trigger",
                "type": "n8n-nodes-base.scheduleTrigger",
                "parameters": {
                    "rule": {
                        "interval": [{"field": "hours", "hoursInterval": 24}]
                    }
                },
                "position": [250, 300],
                "typeVersion": 1
            },
            {
                "name": "Get Topics",
                "type": "n8n-nodes-base.googleSheets",
                "parameters": {
                    "operation": "read"
                },
                "position": [450, 300],
                "typeVersion": 3
            },
            {
                "name": "Generate Article",
                "type": "@n8n/n8n-nodes-langchain.openAi",
                "parameters": {
                    "model": "gpt-4o-mini",
                    "messages": {
                        "values": [
                            {
                                "content": "Напиши статью:\nТема: {{$json.topic}}\nСтиль: {style}\nОбъём: {word_count} слов\nSEO-ключи: {{$json.keywords}}"
                            }
                        ]
                    }
                },
                "position": [650, 300],
                "typeVersion": 1
            },
            {
                "name": "Save to Google Docs",
                "type": "n8n-nodes-base.googleDocs",
                "parameters": {
                    "operation": "create"
                },
                "position": [850, 300],
                "typeVersion": 1
            },
            {
                "name": "Notify",
                "type": "n8n-nodes-base.telegram",
                "parameters": {
                    "operation": "sendMessage",
                    "chatId": "{my_chat_id}",
                    "text": "📝 Готова статья: {{$json.topic}}\nСсылка: {{$json.doc_url}}"
                },
                "position": [1050, 300],
                "typeVersion": 1
            }
        ],
        "connections": {
            "Daily Trigger": {"main": [[{"node": "Get Topics", "type": "main", "index": 0}]]},
            "Get Topics": {"main": [[{"node": "Generate Article", "type": "main", "index": 0}]]},
            "Generate Article": {"main": [[{"node": "Save to Google Docs", "type": "main", "index": 0}]]},
            "Save to Google Docs": {"main": [[{"node": "Notify", "type": "main", "index": 0}]]}
        }
    },
    
    "bot_development": {
        "name": "Telegram Bot — {client}",
        "nodes": [
            {
                "name": "Telegram Trigger",
                "type": "n8n-nodes-base.telegramTrigger",
                "parameters": {
                    "updates": ["message"]
                },
                "position": [250, 300],
                "typeVersion": 1,
                "webhookId": "{WEBHOOK_ID}"
            },
            {
                "name": "AI Response",
                "type": "@n8n/n8n-nodes-langchain.openAi",
                "parameters": {
                    "model": "gpt-4o-mini",
                    "messages": {
                        "values": [
                            {
                                "role": "system",
                                "content": "{bot_system_prompt}"
                            },
                            {
                                "role": "user",
                                "content": "={{$json.message.text}}"
                            }
                        ]
                    }
                },
                "position": [450, 300],
                "typeVersion": 1
            },
            {
                "name": "Send Reply",
                "type": "n8n-nodes-base.telegram",
                "parameters": {
                    "operation": "sendMessage",
                    "chatId": "={{$json.message.chat.id}}",
                    "text": "={{$json.response}}"
                },
                "position": [650, 300],
                "typeVersion": 1
            }
        ],
        "connections": {
            "Telegram Trigger": {"main": [[{"node": "AI Response", "type": "main", "index": 0}]]},
            "AI Response": {"main": [[{"node": "Send Reply", "type": "main", "index": 0}]]}
        }
    },
    
    "data_processing": {
        "name": "Reports & Analytics — {client}",
        "nodes": [
            {
                "name": "Weekly Schedule",
                "type": "n8n-nodes-base.scheduleTrigger",
                "parameters": {
                    "rule": {
                        "interval": [{"field": "weeks", "weeksInterval": 1}]
                    }
                },
                "position": [250, 300],
                "typeVersion": 1
            },
            {
                "name": "Fetch Data",
                "type": "n8n-nodes-base.httpRequest",
                "parameters": {
                    "url": "{data_source_url}",
                    "method": "GET"
                },
                "position": [450, 300],
                "typeVersion": 4
            },
            {
                "name": "Process Data",
                "type": "n8n-nodes-base.code",
                "parameters": {
                    "jsCode": "// Обработка и агрегация данных\nconst data = $input.all();\n// Твоя логика обработки\nreturn data;"
                },
                "position": [650, 300],
                "typeVersion": 2
            },
            {
                "name": "AI Summary",
                "type": "@n8n/n8n-nodes-langchain.openAi",
                "parameters": {
                    "model": "gpt-4o-mini",
                    "messages": {
                        "values": [
                            {
                                "content": "Проанализируй данные и напиши краткий отчёт с выводами:\n{{$json.aggregated_data}}"
                            }
                        ]
                    }
                },
                "position": [850, 300],
                "typeVersion": 1
            },
            {
                "name": "Send Report",
                "type": "n8n-nodes-base.telegram",
                "parameters": {
                    "operation": "sendMessage",
                    "chatId": "{ЗАПОЛНИ_CLIENT_CHAT_ID}",
                    "text": "📊 Еженедельный отчёт:\n{{$json.summary}}"
                },
                "position": [1050, 300],
                "typeVersion": 1
            }
        ],
        "connections": {
            "Weekly Schedule": {"main": [[{"node": "Fetch Data", "type": "main", "index": 0}]]},
            "Fetch Data": {"main": [[{"node": "Process Data", "type": "main", "index": 0}]]},
            "Process Data": {"main": [[{"node": "AI Summary", "type": "main", "index": 0}]]},
            "AI Summary": {"main": [[{"node": "Send Report", "type": "main", "index": 0}]]}
        }
    },
    
    "email_outreach": {
        "name": "Email Outreach — {client}",
        "nodes": [
            {
                "name": "Daily Schedule",
                "type": "n8n-nodes-base.scheduleTrigger",
                "parameters": {
                    "rule": {
                        "interval": [{"field": "hours", "hoursInterval": 24}]
                    }
                },
                "position": [250, 300],
                "typeVersion": 1
            },
            {
                "name": "Get Leads",
                "type": "n8n-nodes-base.googleSheets",
                "parameters": {
                    "operation": "read"
                },
                "position": [450, 300],
                "typeVersion": 3
            },
            {
                "name": "Personalize Email",
                "type": "@n8n/n8n-nodes-langchain.openAi",
                "parameters": {
                    "model": "gpt-4o-mini",
                    "messages": {
                        "values": [
                            {
                                "content": "Напиши персонализированное письмо:\nКому: {{$json.name}} ({{$json.company}})\nЦель: {goal}\nТон: деловой но дружелюбный"
                            }
                        ]
                    }
                },
                "position": [650, 300],
                "typeVersion": 1
            },
            {
                "name": "Send Email",
                "type": "n8n-nodes-base.emailSend",
                "parameters": {
                    "fromEmail": "{sender_email}",
                    "toEmail": "={{$json.email}}",
                    "subject": "={{$json.subject}}",
                    "text": "={{$json.personalized_text}}"
                },
                "position": [850, 300],
                "typeVersion": 2
            },
            {
                "name": "Log Sent",
                "type": "n8n-nodes-base.googleSheets",
                "parameters": {
                    "operation": "update"
                },
                "position": [1050, 300],
                "typeVersion": 3
            }
        ],
        "connections": {
            "Daily Schedule": {"main": [[{"node": "Get Leads", "type": "main", "index": 0}]]},
            "Get Leads": {"main": [[{"node": "Personalize Email", "type": "main", "index": 0}]]},
            "Personalize Email": {"main": [[{"node": "Send Email", "type": "main", "index": 0}]]},
            "Send Email": {"main": [[{"node": "Log Sent", "type": "main", "index": 0}]]}
        }
    }
}


class WorkflowBuilder:
    """Автоматический сборщик n8n workflows"""
    
    def __init__(self):
        self.n8n_url = config.n8n_url
        self.n8n_headers = {
            'X-N8N-API-KEY': config.n8n_api_key,
            'Content-Type': 'application/json'
        }
    
    async def build(self, project_id: int, analysis: dict, vacancy: dict) -> dict:
        """
        Главный метод: собирает workflow и деплоит в n8n
        
        Args:
            project_id: ID проекта в БД
            analysis: Результаты AI-анализа
            vacancy: Данные вакансии
            
        Returns:
            dict с информацией о созданном workflow
        """
        
        automation_type = analysis.get('automation_type', 'other')
        template = WORKFLOW_TEMPLATES.get(automation_type)
        
        if not template:
            # Если нет готового шаблона — создаём базовый
            workflow = self._create_basic_workflow(analysis, vacancy)
        else:
            # Кастомизируем шаблон
            workflow = self._customize_template(template, analysis, vacancy)
        
        # Деплой в n8n
        n8n_result = await self._deploy_to_n8n(workflow)
        
        # Генерация инструкции
        instructions = self._generate_instructions(analysis, workflow, n8n_result)
        
        # Сохранение в БД
        db.update_project(
            project_id,
            n8n_workflow_id=n8n_result.get('id', 'local'),
            workflow_json=json.dumps(workflow, ensure_ascii=False),
            status='ready'
        )
        
        return {
            'workflow': workflow,
            'n8n_id': n8n_result.get('id'),
            'n8n_url': n8n_result.get('url', ''),
            'instructions': instructions,
            'status': n8n_result.get('status', 'unknown')
        }
    
    def _customize_template(self, template: dict, analysis: dict, vacancy: dict) -> dict:
        """Кастомизация шаблона под конкретную вакансию"""
        
        # Deep copy
        workflow = json.loads(json.dumps(template))
        
        # Извлекаем данные
        client_name = vacancy['title'][:30].replace('/', '-')
        plan = analysis.get('automation_plan', {})
        
        # Замены
        replacements = {
            '{client}': client_name,
            '{my_chat_id}': str(config.my_chat_id),
            '{business_type}': vacancy.get('description', '')[:100],
            '{tone}': 'дружелюбный профессиональный',
            '{length}': '200',
            '{style}': 'информативный',
            '{word_count}': '1000',
            '{source_url}': '{ЗАПОЛНИ_URL_ИСТОЧНИКА}',
            '{selector}': '{ЗАПОЛНИ_CSS_СЕЛЕКТОР}',
            '{goal}': 'предложить услуги',
            '{sender_email}': '{ЗАПОЛНИ_EMAIL}',
            '{data_source_url}': '{ЗАПОЛНИ_URL}',
            '{bot_system_prompt}': 'Ты помощник компании. Отвечай вежливо и по делу.',
        }
        
        # Применяем замены
        workflow_str = json.dumps(workflow, ensure_ascii=False)
        for key, value in replacements.items():
            workflow_str = workflow_str.replace(key, value)
        
        return json.loads(workflow_str)
    
    def _create_basic_workflow(self, analysis: dict, vacancy: dict) -> dict:
        """Создание базового workflow если нет шаблона"""
        
        client_name = vacancy['title'][:30].replace('/', '-')
        
        return {
            "name": f"Custom Workflow — {client_name}",
            "nodes": [
                {
                    "name": "Manual Trigger",
                    "type": "n8n-nodes-base.manualTrigger",
                    "parameters": {},
                    "position": [250, 300],
                    "typeVersion": 1
                },
                {
                    "name": "Code Placeholder",
                    "type": "n8n-nodes-base.code",
                    "parameters": {
                        "jsCode": "// TODO: Реализовать логику\n// План:\n" + 
                                  "\n".join(f"// {step}" for step in analysis.get('automation_plan', {}).get('steps', []))
                    },
                    "position": [450, 300],
                    "typeVersion": 2
                }
            ],
            "connections": {
                "Manual Trigger": {"main": [[{"node": "Code Placeholder", "type": "main", "index": 0}]]}
            }
        }
    
    async def _deploy_to_n8n(self, workflow: dict) -> dict:
        """Деплой workflow в n8n через REST API"""
        
        if not config.n8n_api_key:
            # Если нет API ключа — сохраняем локально
            return self._save_locally(workflow)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f'{self.n8n_url}/api/v1/workflows',
                    headers=self.n8n_headers,
                    json={
                        'name': workflow.get('name', 'Auto-generated Workflow'),
                        'nodes': workflow.get('nodes', []),
                        'connections': workflow.get('connections', {}),
                        'active': False,
                        'settings': {}
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    workflow_id = result.get('id', 'unknown')
                    
                    return {
                        'id': workflow_id,
                        'url': f"{self.n8n_url}/workflow/{workflow_id}",
                        'status': 'created'
                    }
                else:
                    print(f"⚠️ n8n вернул код {response.status_code}")
                    return self._save_locally(workflow)
        
        except Exception as e:
            print(f"❌ Ошибка деплоя в n8n: {e}")
            return self._save_locally(workflow)
    
    def _save_locally(self, workflow: dict) -> dict:
        """Сохранение workflow локально как фоллбэк"""
        
        os.makedirs('workflows', exist_ok=True)
        
        filename = f"workflows/workflow_{workflow.get('name', 'unknown').replace(' ', '_')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(workflow, f, ensure_ascii=False, indent=2)
        
        return {
            'id': 'local',
            'url': f'file://{os.path.abspath(filename)}',
            'status': 'saved_locally',
            'file': filename
        }
    
    def _generate_instructions(self, analysis: dict, workflow: dict, n8n_result: dict) -> str:
        """Генерация инструкции для запуска"""
        
        plan = analysis.get('automation_plan', {})
        apis = plan.get('apis_needed', [])
        manual = analysis.get('manual_work', 'нет')
        
        instructions = f"""
📋 ИНСТРУКЦИЯ ПО ЗАПУСКУ WORKFLOW

1️⃣ WORKFLOW СОЗДАН
   {"✅ Задеплоен в n8n: " + n8n_result.get('id', '') if n8n_result.get('status') == 'created' else "📁 Сохранён локально: " + n8n_result.get('file', '')}
   🔗 {n8n_result.get('url', '')}

2️⃣ НАСТРОЙКА API И CREDENTIALS
   {"   • Подключить " + chr(10).join(f"   • {api}" for api in apis) if apis else "   Нет внешних API"}
   • Заполнить все плейсхолдеры {{ЗАПОЛНИ_...}}
   • Настроить credentials в n8n

3️⃣ РУЧНАЯ РАБОТА
   {manual}

4️⃣ ТЕСТИРОВАНИЕ
   • Открыть workflow в n8n
   • Нажать "Execute Workflow" для теста
   • Проверить все шаги на ошибки
   • При необходимости — скорректировать

5️⃣ АКТИВАЦИЯ
   • После успешного теста — включить "Active"
   • Настроить алерты на ошибки (Settings → Error Workflow)
   • Мониторить первые 24-48 часов

6️⃣ ПОДДЕРЖКА
   • ~{analysis.get('hours_monthly_support', 2)} ч/месяц на обслуживание
   • Проверять логи раз в неделю
   • Обновлять контент/данные по расписанию

💡 СОВЕТЫ:
   • Сделай бэкап workflow перед изменениями
   • Используй Environment Variables для секретов
   • Настрой Telegram-уведомления об ошибках
"""
        return instructions


# Глобальный экземпляр
builder = WorkflowBuilder()
