"""Управление базой данных SQLite"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict
from contextlib import contextmanager

from src.config import config


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.db_path
        self.init_db()
    
    @contextmanager
    def get_conn(self):
        """Контекстный менеджер для подключения к БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_db(self):
        """Инициализация таблиц"""
        
        with self.get_conn() as conn:
            conn.executescript('''
                -- Таблица вакансий
                CREATE TABLE IF NOT EXISTS vacancies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hash TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    salary INTEGER DEFAULT 0,
                    salary_min INTEGER,
                    salary_max INTEGER,
                    salary_currency TEXT DEFAULT 'RUB',
                    description TEXT,
                    raw_text TEXT,
                    source TEXT,
                    link TEXT,
                    company TEXT,
                    location TEXT,
                    employment_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'new'
                );
                
                CREATE INDEX IF NOT EXISTS idx_vacancies_hash ON vacancies(hash);
                CREATE INDEX IF NOT EXISTS idx_vacancies_status ON vacancies(status);
                CREATE INDEX IF NOT EXISTS idx_vacancies_created ON vacancies(created_at);
                
                -- Таблица AI-анализа
                CREATE TABLE IF NOT EXISTS analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vacancy_id INTEGER UNIQUE NOT NULL,
                    recommendation TEXT,
                    match_percent INTEGER,
                    automation_type TEXT,
                    hours_estimate INTEGER,
                    hours_setup INTEGER,
                    hours_monthly_support INTEGER,
                    costs INTEGER,
                    profit INTEGER,
                    roi REAL,
                    automation_percent INTEGER,
                    automation_plan TEXT,
                    manual_work TEXT,
                    scalable BOOLEAN,
                    scale_potential TEXT,
                    risks TEXT,
                    reasoning TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (vacancy_id) REFERENCES vacancies(id) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_analysis_vacancy ON analysis(vacancy_id);
                
                -- Таблица проектов
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vacancy_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'building',
                    n8n_workflow_id TEXT,
                    workflow_json TEXT,
                    scripts TEXT,
                    client_notes TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    actual_hours REAL DEFAULT 0,
                    actual_income INTEGER DEFAULT 0,
                    FOREIGN KEY (vacancy_id) REFERENCES vacancies(id) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
                CREATE INDEX IF NOT EXISTS idx_projects_vacancy ON projects(vacancy_id);
                
                -- Таблица статистики
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    vacancies_found INTEGER DEFAULT 0,
                    vacancies_filtered INTEGER DEFAULT 0,
                    vacancies_recommended INTEGER DEFAULT 0,
                    projects_taken INTEGER DEFAULT 0,
                    total_profit INTEGER DEFAULT 0,
                    avg_roi REAL DEFAULT 0
                );
            ''')
    
    def vacancy_exists(self, hash: str) -> bool:
        """Проверка существования вакансии по хешу"""
        
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT id FROM vacancies WHERE hash = ?", 
                (hash,)
            ).fetchone()
            return row is not None
    
    def save_vacancy(self, data: dict) -> Optional[int]:
        """Сохранение вакансии в БД"""
        
        with self.get_conn() as conn:
            try:
                cursor = conn.execute('''
                    INSERT INTO vacancies 
                    (hash, title, salary, salary_min, salary_max, salary_currency,
                     description, raw_text, source, link, company, location, employment_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['hash'],
                    data['title'],
                    data.get('salary', 0),
                    data.get('salary_min'),
                    data.get('salary_max'),
                    data.get('salary_currency', 'RUB'),
                    data.get('description', ''),
                    data.get('raw_text', ''),
                    data.get('source', ''),
                    data.get('link', ''),
                    data.get('company', ''),
                    data.get('location', ''),
                    data.get('employment_type', '')
                ))
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                # Дубликат - уже существует
                return None
    
    def save_analysis(self, vacancy_id: int, analysis: dict):
        """Сохранение результатов AI-анализа"""
        
        with self.get_conn() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO analysis
                (vacancy_id, recommendation, match_percent, automation_type,
                 hours_estimate, hours_setup, hours_monthly_support,
                 costs, profit, roi, automation_percent,
                 automation_plan, manual_work, scalable, scale_potential,
                 risks, reasoning)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                vacancy_id,
                analysis.get('recommendation', ''),
                analysis.get('match_percent', 0),
                analysis.get('automation_type', ''),
                analysis.get('hours_estimate', 0),
                analysis.get('hours_setup', 0),
                analysis.get('hours_monthly_support', 0),
                analysis.get('costs', 0),
                analysis.get('profit', 0),
                analysis.get('roi', 0),
                analysis.get('automation_percent', 0),
                json.dumps(analysis.get('automation_plan', {}), ensure_ascii=False),
                analysis.get('manual_work', ''),
                analysis.get('scalable', False),
                analysis.get('scale_potential', ''),
                json.dumps(analysis.get('risks', []), ensure_ascii=False),
                analysis.get('reasoning', '')
            ))
    
    def create_project(self, vacancy_id: int) -> int:
        """Создание нового проекта"""
        
        with self.get_conn() as conn:
            cursor = conn.execute('''
                INSERT INTO projects (vacancy_id, status)
                VALUES (?, 'building')
            ''', (vacancy_id,))
            
            # Обновляем статус вакансии
            conn.execute(
                "UPDATE vacancies SET status = 'taken' WHERE id = ?",
                (vacancy_id,)
            )
            
            return cursor.lastrowid
    
    def update_project(self, project_id: int, **kwargs):
        """Обновление данных проекта"""
        
        if not kwargs:
            return
        
        with self.get_conn() as conn:
            sets = ', '.join(f"{k} = ?" for k in kwargs.keys())
            values = list(kwargs.values()) + [project_id]
            
            conn.execute(
                f"UPDATE projects SET {sets} WHERE id = ?",
                values
            )
    
    def get_active_projects_count(self) -> int:
        """Количество активных проектов"""
        
        with self.get_conn() as conn:
            row = conn.execute('''
                SELECT COUNT(*) as cnt 
                FROM projects 
                WHERE status IN ('building', 'active', 'ready')
            ''').fetchone()
            return row['cnt']
    
    def get_vacancy_with_analysis(self, vacancy_id: int) -> Optional[Dict]:
        """Получить вакансию с результатами анализа"""
        
        with self.get_conn() as conn:
            row = conn.execute('''
                SELECT 
                    v.*,
                    a.recommendation, a.match_percent, a.automation_type,
                    a.hours_estimate, a.hours_setup, a.hours_monthly_support,
                    a.costs, a.profit, a.roi, a.automation_percent,
                    a.automation_plan, a.manual_work, a.scalable,
                    a.scale_potential, a.risks, a.reasoning
                FROM vacancies v
                LEFT JOIN analysis a ON v.id = a.vacancy_id
                WHERE v.id = ?
            ''', (vacancy_id,)).fetchone()
            
            return dict(row) if row else None
    
    def get_stats(self) -> Dict:
        """Получить общую статистику"""
        
        with self.get_conn() as conn:
            stats = {}
            
            # Всего найдено
            stats['total_found'] = conn.execute(
                "SELECT COUNT(*) FROM vacancies"
            ).fetchone()[0]
            
            # Активных проектов
            stats['active_projects'] = conn.execute(
                "SELECT COUNT(*) FROM projects WHERE status IN ('building', 'active', 'ready')"
            ).fetchone()[0]
            
            # Всего заработано
            stats['total_earned'] = conn.execute(
                "SELECT COALESCE(SUM(actual_income), 0) FROM projects WHERE actual_income > 0"
            ).fetchone()[0]
            
            # Средний профит по рекомендованным
            stats['avg_profit'] = conn.execute(
                "SELECT COALESCE(AVG(profit), 0) FROM analysis WHERE recommendation = 'Брать'"
            ).fetchone()[0]
            
            # Средний ROI
            stats['avg_roi'] = conn.execute(
                "SELECT COALESCE(AVG(roi), 0) FROM analysis WHERE recommendation = 'Брать'"
            ).fetchone()[0]
            
            # Проектов завершено
            stats['completed_projects'] = conn.execute(
                "SELECT COUNT(*) FROM projects WHERE status = 'completed'"
            ).fetchone()[0]
            
            return stats
    
    def update_daily_stats(self, increment: dict):
        """Обновление дневной статистики"""
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        with self.get_conn() as conn:
            # Получаем текущие значения
            row = conn.execute(
                "SELECT * FROM daily_stats WHERE date = ?",
                (today,)
            ).fetchone()
            
            if row:
                # Обновляем
                updates = []
                values = []
                for key, value in increment.items():
                    updates.append(f"{key} = {key} + ?")
                    values.append(value)
                values.append(today)
                
                conn.execute(
                    f"UPDATE daily_stats SET {', '.join(updates)} WHERE date = ?",
                    values
                )
            else:
                # Создаём новую запись
                conn.execute(
                    "INSERT INTO daily_stats (date) VALUES (?)",
                    (today,)
                )
                # Повторяем обновление
                self.update_daily_stats(increment)


# Глобальный экземпляр БД
db = Database()
