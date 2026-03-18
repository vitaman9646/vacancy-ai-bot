import asyncio
from src.analyzer import analyzer

async def test():
    vacancy = {
        'title': 'SMM-менеджер для стоматологии (удалённо)',
        'salary': 60000,
        'salary_min': 50000,
        'salary_max': 70000,
        'description': '''
Ищем SMM-менеджера для ведения соцсетей стоматологической клиники.

Обязанности:
- Создание контент-плана на месяц
- Публикация постов в Instagram, VK, Telegram
- Ответы на комментарии клиентов
- Анализ эффективности публикаций

Требования:
- Опыт работы SMM от 1 года
- Знание Canva, Photoshop базово
- Грамотная речь и письмо
- Понимание медицинской тематики приветствуется

Условия:
- Полностью удалённая работа
- Гибкий график
- Оплата 60000 руб/месяц
- Возможность роста до 80000
        ''',
        'link': 'https://example.com/vacancy/123'
    }
    
    print("=" * 70)
    print("🧠 ТЕСТ AI-АНАЛИЗА")
    print("=" * 70)
    print("")
    print(f"Вакансия: {vacancy['title']}")
    print(f"Зарплата: {vacancy['salary']} ₽")
    print("")
    print("Запуск анализа...\n")
    
    try:
        analysis = await analyzer.analyze(vacancy)
        
        print("✅ АНАЛИЗ ЗАВЕРШЁН!\n")
        print("=" * 70)
        print(f"Рекомендация: {analysis['recommendation']}")
        print(f"Совпадение: {analysis.get('match_percent', 0)}%")
        print(f"Профит: {analysis['profit']:,} ₽")
        print(f"ROI: {analysis['roi']}%")
        print(f"Часов работы: {analysis['hours_estimate']} ч")
        print(f"Автоматизация: {analysis['automation_percent']}%")
        print(f"Тип: {analysis['automation_type']}")
        print("")
        print("ПЛАН АВТОМАТИЗАЦИИ:")
        print(f"  {analysis['automation_plan'].get('title', 'N/A')}")
        print("")
        print("Шаги:")
        for step in analysis['automation_plan'].get('steps', [])[:5]:
            print(f"  • {step}")
        print("")
        print("Необходимые API:")
        for api in analysis['automation_plan'].get('apis_needed', []):
            print(f"  • {api}")
        print("")
        print(f"Масштабируемость: {'✅ Да' if analysis.get('scalable') else '❌ Нет'}")
        print(f"Потенциал: {analysis.get('scale_potential', 'нет')}")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test())
