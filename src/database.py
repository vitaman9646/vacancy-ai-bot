# src/database.py

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict
from contextlib import contextmanager
from src.config import config  # Используем путь к БД из конфига

class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.db_path
        self.init_db()

    # ... остальной код без изменений
