"""Парсеры источников вакансий"""

from .base import BaseParser, Vacancy
from .kadrout import KadroutParser
from .telegram import TelegramParser, telegram_parser

__all__ = [
    'BaseParser', 
    'Vacancy', 
    'KadroutParser', 
    'TelegramParser',
    'telegram_parser'
]
