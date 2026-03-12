"""Парсер для kadrout.ru (SPA, требует Selenium)"""

import asyncio
import re
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import undetected_chromedriver as uc

from .base import BaseParser, Vacancy


class KadroutParser(BaseParser):
    """Парсер для kadrout.ru"""
    
    BASE_URL = 'https://kadrout.ru'
    
    # Актуальные селекторы (март 2026)
    SELECTORS = {
        'vacancy_cards': [
            '.vacancy-card',
            '.vacancy-item', 
            'div[class*="vacancy"]',
            'article[class*="job"]',
            'div[class*="card"]',
            '[data-vacancy-id]',
        ],
        'card_title': [
            'h1', 'h2', 'h3', 
            '[class*="title"]',
            '[class*="name"]',
            'a.vacancy-title',
        ],
        'card_link': ['a[href*="/vacancies/"]', 'a[href]'],
        'card_salary': [
            '[class*="salary"]',
            '[class*="price"]', 
            '[class*="wage"]',
            'span:contains("₽")',
        ],
        'detail_description': [
            '[class*="description"]',
            '[class*="content"]',
            'article',
            'main',
            '[class*="text"]',
            '.vacancy__desc',
            '.job-content',
        ],
        'detail_company': [
            '[class*="company"]',
            '[class*="employer"]',
        ],
        'detail_location': [
            '[class*="location"]',
            '[class*="city"]',
            '[class*="address"]',
        ],
    }
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
    
    def _init_driver(self):
        """Инициализация Selenium WebDriver с защитой от детекта"""
        if self.driver:
            return
        
        options = uc.ChromeOptions()
        
        if self.headless:
            options.add_argument('--headless=new')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
        
        # Используем undetected-chromedriver для обхода защиты
        self.driver = uc.Chrome(
            options=options,
            version_main=None,  # Авто-определение версии Chrome
        )
        
        # Увеличиваем timeout
        self.driver.set_page_load_timeout(30)
        self.driver.implicitly_wait(10)
    
    def _close_driver(self):
        """Закрытие драйвера"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def _find_element_by_selectors(
        self, 
        soup: BeautifulSoup, 
        selectors: List[str]
    ) -> Optional[str]:
        """Поиск элемента по списку селекторов"""
        for selector in selectors:
            try:
                el = soup.select_one(selector)
                if el:
                    return el
            except:
                continue
        return None
    
    def _extract_salary(self, text: str) -> dict:
        """
        Извлечение зарплаты из текста
        
        Поддерживаемые форматы:
        - "45000 - 60000 ₽"
        - "От 25000 ₽"
        - "60000 - 120000 ₽"
        - "договорная"
        - "$1000 - $2000"
        """
        if not text:
            return {'min': None, 'max': None, 'currency': 'RUB'}
        
        text = text.replace('\xa0', ' ').replace(',', '')
        
        # Проверка на "договорная"
        if re.search(r'договор|negotiable|по\s*согласованию', text, re.I):
            return {'min': 0, 'max': 0, 'currency': 'RUB'}
        
        # Определение валюты
        currency = 'RUB'
        if '$' in text or 'usd' in text.lower() or 'dollar' in text.lower():
            currency = 'USD'
        elif '€' in text or 'eur' in text.lower():
            currency = 'EUR'
        
        patterns = [
            # Диапазон: "45000 - 60000"
            r'(\d[\d\s]*)\s*[-–—]\s*(\d[\d\s]*)',
            
            # "От X до Y"
            r'(?:от|from)\s*(\d[\d\s]*)\s*(?:до|to)\s*(\d[\d\s]*)',
            
            # "От X"
            r'(?:от|from|от\s*)\s*(\d[\d\s]*)',
            
            # "До X"
            r'(?:до|to|up\s*to)\s*(\d[\d\s]*)',
            
            # Просто число
            r'(\d[\d\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = [g for g in match.groups() if g]
                
                if len(groups) >= 2:
                    # Диапазон
                    min_val = int(groups[0].replace(' ', ''))
                    max_val = int(groups[1].replace(' ', ''))
                    
                    # Проверка на "к" (тысячи)
                    if min_val < 1000 and ('к' in text.lower() or 'k' in text.lower()):
                        min_val *= 1000
                        max_val *= 1000
                    
                    return {'min': min_val, 'max': max_val, 'currency': currency}
                
                elif len(groups) == 1:
                    # Одно значение
                    val = int(groups[0].replace(' ', ''))
                    
                    if val < 1000 and ('к' in text.lower() or 'k' in text.lower()):
                        val *= 1000
                    
                    # "От X" = min, "До X" = max
                    if re.search(r'(?:от|from)', text, re.I):
                        return {'min': val, 'max': None, 'currency': currency}
                    elif re.search(r'(?:до|to|up)', text, re.I):
                        return {'min': None, 'max': val, 'currency': currency}
                    else:
                        return {'min': val, 'max': val, 'currency': currency}
        
        return {'min': None, 'max': None, 'currency': currency}
    
    async def fetch_vacancies(self, limit: int = 20) -> List[Vacancy]:
        """Получить список вакансий со страницы списка"""
        
        # Запускаем в отдельном потоке, т.к. Selenium синхронный
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self._fetch_vacancies_sync, 
            limit
        )
    
    def _fetch_vacancies_sync(self, limit: int) -> List[Vacancy]:
        """Синхронное получение вакансий (для run_in_executor)"""
        
        self._init_driver()
        vacancies = []
        
        try:
            # Загрузка главной страницы
            self.driver.get(f'{self.BASE_URL}/vacancies')
            
            # Ожидание загрузки (можно улучшить под конкретный селектор)
            wait = WebDriverWait(self.driver, 15)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            
            # Дополнительная задержка для JS
            asyncio.sleep(2)
            
            # Получение HTML после рендера
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Поиск карточек вакансий
            cards = []
            for selector in self.SELECTORS['vacancy_cards']:
                cards = soup.select(selector)
                if cards:
                    print(f"✅ Найдено {len(cards)} карточек по селектору: {selector}")
                    break
            
            if not cards:
                print("⚠️ Карточки вакансий не найдены!")
                # Сохраняем HTML для дебага
                with open('/tmp/kadrout_debug.html', 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())
                return []
            
            # Парсинг каждой карточки
            for card in cards[:limit]:
                try:
                    vacancy = self._parse_card(card)
                    if vacancy:
                        vacancies.append(vacancy)
                except Exception as e:
                    print(f"Ошибка парсинга карточки: {e}")
                    continue
        
        finally:
            # НЕ закрываем драйвер здесь — переиспользуем
            pass
        
        return vacancies
    
    def _parse_card(self, card) -> Optional[Vacancy]:
        """Парсинг одной карточки вакансии"""
        
        # Заголовок
        title_el = self._find_element_by_selectors(
            card, 
            self.SELECTORS['card_title']
        )
        if not title_el:
            return None
        
        title = title_el.get_text(strip=True)
        
        # Ссылка
        link_el = self._find_element_by_selectors(
            card,
            self.SELECTORS['card_link']
        )
        if not link_el:
            return None
        
        link = link_el.get('href', '')
        if not link.startswith('http'):
            link = self.BASE_URL + link
        
        # Зарплата
        salary_el = self._find_element_by_selectors(
            card,
            self.SELECTORS['card_salary']
        )
        
        salary_data = {'min': None, 'max': None, 'currency': 'RUB'}
        if salary_el:
            salary_text = salary_el.get_text(strip=True)
            salary_data = self._extract_salary(salary_text)
        
        # Краткое описание
        preview = card.get_text(separator=' ', strip=True)[:300]
        
        return Vacancy(
            title=title,
            link=link,
            salary_min=salary_data['min'],
            salary_max=salary_data['max'],
            salary_currency=salary_data['currency'],
            raw_text=preview,
            source='kadrout_website',
        )
    
    async def fetch_vacancy_details(self, url: str) -> Optional[Vacancy]:
        """Получить детальную информацию о вакансии"""
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._fetch_vacancy_details_sync,
            url
        )
    
    def _fetch_vacancy_details_sync(self, url: str) -> Optional[Vacancy]:
        """Синхронное получение деталей вакансии"""
        
        self._init_driver()
        
        try:
            self.driver.get(url)
            
            wait = WebDriverWait(self.driver, 15)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'article')))
            
            asyncio.sleep(1)
            
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Заголовок
            title_el = soup.select_one('h1')
            title = title_el.get_text(strip=True) if title_el else 'Без названия'
            
            # Описание
            desc_el = self._find_element_by_selectors(
                soup,
                self.SELECTORS['detail_description']
            )
            description = desc_el.get_text(separator='\n', strip=True) if desc_el else ''
            
            # Зарплата (может быть в описании)
            salary_data = self._extract_salary(soup.get_text())
            
            # Компания
            company_el = self._find_element_by_selectors(
                soup,
                self.SELECTORS['detail_company']
            )
            company = company_el.get_text(strip=True) if company_el else ''
            
            # Локация
            location_el = self._find_element_by_selectors(
                soup,
                self.SELECTORS['detail_location']
            )
            location = location_el.get_text(strip=True) if location_el else ''
            
            # Определение типа занятости
            employment_type = 'unknown'
            desc_lower = description.lower()
            if any(kw in desc_lower for kw in ['удалённо', 'remote', 'удаленно']):
                employment_type = 'remote'
            elif any(kw in desc_lower for kw in ['офис', 'office']):
                employment_type = 'office'
            elif any(kw in desc_lower for kw in ['гибрид', 'hybrid']):
                employment_type = 'hybrid'
            
            return Vacancy(
                title=title,
                link=url,
                salary_min=salary_data['min'],
                salary_max=salary_data['max'],
                salary_currency=salary_data['currency'],
                description=description,
                raw_text=description,
                source='kadrout_website',
                company=company,
                location=location,
                employment_type=employment_type,
            )
        
        except Exception as e:
            print(f"Ошибка получения деталей {url}: {e}")
            return None
    
    def __del__(self):
        """Очистка при удалении объекта"""
        self._close_driver()
