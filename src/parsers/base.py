"""Базовый класс для всех парсеров"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class Vacancy:
    """Универсальная структура вакансии"""
    title: str
    link: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = 'RUB'
    description: str = ''
    raw_text: str = ''
    source: str = ''
    company: str = ''
    location: str = ''
    employment_type: str = ''  # удалённо/офис/гибрид
    experience: str = ''
    
    @property
    def salary(self) -> int:
        """Средняя зарплата для фильтров"""
        if self.salary_min and self.salary_max:
            return (self.salary_min + self.salary_max) // 2
        return self.salary_min or self.salary_max or 0
    
    def to_dict(self) -> dict:
        return {
            'title': self.title,
            'salary': self.salary,
            'salary_min': self.salary_min,
            'salary_max': self.salary_max,
            'description': self.description,
            'raw_text': self.raw_text,
            'source': self.source,
            'link': self.link,
            'company': self.company,
            'location': self.location,
            'employment_type': self.employment_type,
        }


class BaseParser(ABC):
    """Базовый класс для парсеров"""
    
    @abstractmethod
    async def fetch_vacancies(self, limit: int = 20) -> List[Vacancy]:
        """Получить список вакансий"""
        pass
    
    @abstractmethod
    async def fetch_vacancy_details(self, url: str) -> Optional[Vacancy]:
        """Получить детали вакансии"""
        pass
