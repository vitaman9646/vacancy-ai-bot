"""Базовый класс для парсеров"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


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
    employment_type: str = ''  # remote/office/hybrid
    experience: str = ''
    
    @property
    def salary(self) -> int:
        """Средняя зарплата для фильтров"""
        if self.salary_min and self.salary_max:
            return (self.salary_min + self.salary_max) // 2
        return self.salary_min or self.salary_max or 0
    
    def to_dict(self) -> dict:
        """Конвертация в словарь"""
        data = asdict(self)
        data['salary'] = self.salary
        return data


class BaseParser(ABC):
    """Базовый абстрактный класс для всех парсеров"""
    
    @abstractmethod
    async def fetch_vacancies(self, limit: int = 20) -> List[Vacancy]:
        """
        Получить список вакансий
        
        Args:
            limit: Максимальное количество вакансий
            
        Returns:
            Список объектов Vacancy
        """
        pass
    
    @abstractmethod
    async def fetch_vacancy_details(self, url: str) -> Optional[Vacancy]:
        """
        Получить детальную информацию о вакансии
        
        Args:
            url: Ссылка на вакансию
            
        Returns:
            Объект Vacancy с полной информацией или None
        """
        pass
