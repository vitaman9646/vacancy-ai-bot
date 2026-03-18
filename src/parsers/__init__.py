"""Парсеры источников вакансий"""

from .base import BaseParser, Vacancy
from .kadrout import KadroutParser

__all__ = ['BaseParser', 'Vacancy', 'KadroutParser']
