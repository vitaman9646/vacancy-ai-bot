"""Парсер для kadrout.ru (SPA с динамической загрузкой)"""

import asyncio
import re
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import undetected_chromedriver as uc

from .base import BaseParser, Vacancy
from src.config import config


class KadroutParser(BaseParser):
    """Парсер для kadrout.ru с использованием Selenium"""
    
    BASE_URL = 'https://kadrout.ru'
    
    # Селекторы (актуальны на март 2026)
    SELECTORS = {
        'vacancy_cards': [
            '.vacancy-card',
            '.vacancy-item',
            'div[class*="vacancy"]',
            'article[class*="job"]',
            '[data-vacancy-id]',
        ],
        'card_title': [
            'h1', 'h2', 'h3',
            '[class*="title"]',
            '[class*="name"]',
            'a.vacancy-title',
        ],
        'card_link': [
            'a[href*="/vacancies/"]',
            'a[href]'
        ],
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
        ],
        'detail_company': [
            '[class*="company"]',
            '[class*="employer"]',
        ],
        'detail_location': [
            '[class*="location"]',
            '[class*="city"]',
        ],
    }
    
    # Singleton для драйвера
    _driver_instance = None
    _driver_lock = asyncio.Lock()
    
    def __init__(self, headless: bool = None):
        self.headless = headless if headless is not None else config.selenium_headless
        self.driver = None
    
    @classmethod
    async def get_shared_driver(cls, headless=True):
        """Получить переиспользуемый драйвер"""
        async with cls._driver_lock:
            if cls._driver_instance is None:
                loop = asyncio.get_event_loop()
                cls._driver_instance = await loop.run_in_executor(
                    None,
                    cls._create_driver,
                    headless
                )
            return cls._driver_instance
    
    @staticmethod
    def _create_driver(headless=True):
        """Создание драйвера (в отдельном потоке)"""
        options = uc.ChromeOptions()
        
        if headless:
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
        
        driver = uc.Chrome(options=options, version_main=None)
        driver.set_page_load_timeout(config.selenium_timeout)
        driver.implicitly_wait(10)
        
        return driver
    
    def _init_driver(self):
        """Инициализация драйвера"""
        if self.driver:
            return
        
        options = uc.ChromeOptions()
        
        if self.headless:
            options.add_argument('--headless=new')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1920,1080')
        
        self.driver = uc.Chrome(options=options, version_main=None)
        self.driver.set_page_load_timeout(config.selenium_timeout)
    
    def _close_driver(self):
        """Закрытие драйвера"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def _find_element_by_selectors(self, soup: BeautifulSoup, selectors: List[str]):
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
        
        Форматы:
        - "45000 - 60000 ₽"
        - "От 25000 ₽"
        - "договорная"
        """
        if not text:
            return {'min': None, 'max': None, 'currency': 'RUB'}
        
        text = text.replace('\xa0', ' ').replace(',', '')
        
        # Договорная
        if re.search(r'договор|negotiable|по\s*согласованию', text, re.I):
            return {'min': 0, 'max': 0, 'currency': 'RUB'}
        
        # Валюта
        currency = 'RUB'
        if '$' in text or 'usd' in text.lower():
            currency = 'USD'
        elif '€' in text or 'eur' in text.lower():
            currency = 'EUR'
        
        patterns = [
            # Диапазон
            r'(\d[\d\s]*)\s*[-–—]\s*(\d[\d\s]*)',
            # От X до Y
            r'(?:от|from)\s*(\d[\d\s]*)\s*(?:до|to)\s*(\d[\d\s]*)',
            # От X
            r'(?:от|from)\s*(\d[\d\s]*)',
            # До X
            r'(?:до|to|up\s*to)\s*(\d[\d\s]*)',
            # Просто число
            r'(\d[\d\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = [g for g in match.groups() if g]
                
                if len(groups) >= 2:
                    min_val = int(groups[0].replace(' ', ''))
                    max_val = int(groups[1].replace(' ', ''))
                    
                    # Проверка на "к" (тысячи)
                    if min_val < 1000 and ('к' in text.lower() or 'k' in text.lower()):
                        min_val *= 1000
                        max_val *= 1000
                    
                    return {'min': min_val, 'max': max_val, 'currency': currency}
                
                elif len(groups) == 1:
                    val = int(groups[0].replace(' ', ''))
                    
                    if val < 1000 and ('к' in text.lower() or 'k' in text.lower()):
                        val *= 1000
                    
                    if re.search(r'(?:от|from)', text, re.I):
                        return {'min': val, 'max': None, 'currency': currency}
                    elif re.search(r'(?:до|to|up)', text, re.I):
                        return {'min': None, 'max': val, 'currency': currency}
                    else:
                        return {'min': val, 'max': val, 'currency': currency}
        
        return {'min': None, 'max': None, 'currency': currency}
    
    async def fetch_vacancies(self, limit: int = 20) -> List[Vacancy]:
        """Получить список вакансий"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._fetch_vacancies_sync,
            limit
        )
    
    def _fetch_vacancies_sync(self, limit: int) -> List[Vacancy]:
        """Синхронное получение вакансий"""
        self._init_driver()
        vacancies = []
        
        try:
            self.driver.get(f'{self.BASE_URL}/vacancies')
            
            wait = WebDriverWait(self.driver, 15)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            
            # Задержка для загрузки JS
            import time
            time.sleep(2)
            
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Поиск карточек
            cards = []
            for selector in self.SELECTORS['vacancy_cards']:
                cards = soup.select(selector)
                if cards:
                    print(f"✅ Найдено {len(cards)} карточек ({selector})")
                    break
            
            if not cards:
                print("⚠️ Карточки не найдены, сохраняю HTML для отладки...")
                with open('/tmp/kadrout_debug.html', 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())
                return []
            
            for card in cards[:limit]:
                try:
                    vacancy = self._parse_card(card)
                    if vacancy:
                        vacancies.append(vacancy)
                except Exception as e:
                    print(f"⚠️ Ошибка парсинга карточки: {e}")
                    continue
        
        except Exception as e:
            print(f"❌ Ошибка fetch_vacancies: {e}")
        
        return vacancies
    
    def _parse_card(self, card) -> Optional[Vacancy]:
        """Парсинг одной карточки"""
        
        title_el = self._find_element_by_selectors(card, self.SELECTORS['card_title'])
        if not title_el:
            return None
        
        title = title_el.get_text(strip=True)
        
        link_el = self._find_element_by_selectors(card, self.SELECTORS['card_link'])
        if not link_el:
            return None
        
        link = link_el.get('href', '')
        if not link.startswith('http'):
            link = self.BASE_URL + link
        
        salary_el = self._find_element_by_selectors(card, self.SELECTORS['card_salary'])
        salary_data = {'min': None, 'max': None, 'currency': 'RUB'}
        
        if salary_el:
            salary_text = salary_el.get_text(strip=True)
            salary_data = self._extract_salary(salary_text)
        
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
        """Получить детали вакансии"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._fetch_vacancy_details_sync,
            url
        )
    
    def _fetch_vacancy_details_sync(self, url: str) -> Optional[Vacancy]:
        """Синхронное получение деталей"""
        self._init_driver()
        
        try:
            self.driver.get(url)
            
            wait = WebDriverWait(self.driver, 15)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'article')))
            
            import time
            time.sleep(1)
            
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            title_el = soup.select_one('h1')
            title = title_el.get_text(strip=True) if title_el else 'Без названия'
            
            desc_el = self._find_element_by_selectors(soup, self.SELECTORS['detail_description'])
            description = desc_el.get_text(separator='\n', strip=True) if desc_el else ''
            
            salary_data = self._extract_salary(soup.get_text())
            
            company_el = self._find_element_by_selectors(soup, self.SELECTORS['detail_company'])
            company = company_el.get_text(strip=True) if company_el else ''
            
            location_el = self._find_element_by_selectors(soup, self.SELECTORS['detail_location'])
            location = location_el.get_text(strip=True) if location_el else ''
            
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
            print(f"❌ Ошибка получения деталей {url}: {e}")
            return None
    
    def __del__(self):
        """Очистка при удалении"""
        self._close_driver()
