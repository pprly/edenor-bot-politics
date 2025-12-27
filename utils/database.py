"""
База данных для политической системы
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import secrets

from config import DATABASE_PATH


class PoliticsDatabase:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = DATABASE_PATH
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.init_db()
    
    def init_db(self):
        """Инициализация всех таблиц"""
        
        # Партии
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS parties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                ideology TEXT,
                description TEXT,
                leader_telegram_id INTEGER NOT NULL,
                invite_code TEXT UNIQUE,
                registered BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                registration_deadline TIMESTAMP,
                members_count INTEGER DEFAULT 1,
                treasury INTEGER DEFAULT 0,
                channel_id TEXT
            )
        ''')
        
        # Члены партий
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS party_members (
                telegram_id INTEGER,
                minecraft_username TEXT,
                party_id INTEGER,
                role TEXT DEFAULT 'member',
                list_position INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (telegram_id, party_id),
                FOREIGN KEY (party_id) REFERENCES parties(id) ON DELETE CASCADE
            )
        ''')
        
        # Заявки на вступление в партию
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS party_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                minecraft_username TEXT NOT NULL,
                party_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (party_id) REFERENCES parties(id) ON DELETE CASCADE
            )
        ''')
        
        # Парламент
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS parliament (
                telegram_id INTEGER PRIMARY KEY,
                minecraft_username TEXT NOT NULL,
                party_id INTEGER,
                term_start TIMESTAMP,
                term_end TIMESTAMP,
                votes_cast INTEGER DEFAULT 0,
                FOREIGN KEY (party_id) REFERENCES parties(id) ON DELETE SET NULL
            )
        ''')
        
        # Выборы
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS elections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT DEFAULT 'upcoming',
                start_date TIMESTAMP,
                voting_start TIMESTAMP,
                voting_end TIMESTAMP,
                results TEXT
            )
        ''')
        
        # Голоса на выборах
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                election_id INTEGER,
                voter_telegram_id INTEGER,
                party_id INTEGER,
                voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (election_id, voter_telegram_id),
                FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
                FOREIGN KEY (party_id) REFERENCES parties(id) ON DELETE CASCADE
            )
        ''')
        
        # Законопроекты
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS laws (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                author_telegram_id INTEGER,
                status TEXT DEFAULT 'draft',
                votes_for INTEGER DEFAULT 0,
                votes_against INTEGER DEFAULT 0,
                votes_abstain INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                voting_end TIMESTAMP
            )
        ''')
        
        # Голоса депутатов по законам
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS law_votes (
                law_id INTEGER,
                deputy_telegram_id INTEGER,
                vote TEXT,
                voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (law_id, deputy_telegram_id),
                FOREIGN KEY (law_id) REFERENCES laws(id) ON DELETE CASCADE
            )
        ''')
        
        self.db.commit()
    
    # ========== ПАРТИИ ==========
    
    def create_party(self, name: str, ideology: str, description: str, 
                    leader_telegram_id: int, leader_username: str) -> Tuple[int, str]:
        """Создаёт новую партию с кодом приглашения"""
        invite_code = secrets.token_urlsafe(8)
        deadline = datetime.now() + timedelta(hours=24)
        
        cursor = self.db.execute('''
            INSERT INTO parties (name, ideology, description, leader_telegram_id, 
                               invite_code, registration_deadline)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, ideology, description, leader_telegram_id, invite_code, deadline))
        
        party_id = cursor.lastrowid
        
        # Добавляем создателя
        self.db.execute('''
            INSERT INTO party_members (telegram_id, minecraft_username, party_id, role, list_position)
            VALUES (?, ?, ?, 'leader', 1)
        ''', (leader_telegram_id, leader_username, party_id))
        
        self.db.commit()
        return party_id, invite_code
    
    def get_party_by_id(self, party_id: int) -> Optional[Dict]:
        """Получить партию по ID"""
        cursor = self.db.execute('SELECT * FROM parties WHERE id = ?', (party_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_party_by_invite(self, invite_code: str) -> Optional[Dict]:
        """Получить партию по коду приглашения"""
        cursor = self.db.execute('SELECT * FROM parties WHERE invite_code = ?', (invite_code,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_user_party(self, telegram_id: int) -> Optional[Dict]:
        """Получить партию пользователя"""
        cursor = self.db.execute('''
            SELECT p.* FROM parties p
            JOIN party_members pm ON p.id = pm.party_id
            WHERE pm.telegram_id = ?
        ''', (telegram_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def apply_to_party(self, telegram_id: int, minecraft_username: str, party_id: int) -> bool:
        """Подать заявку на вступление в партию"""
        try:
            self.db.execute('''
                INSERT INTO party_applications (telegram_id, minecraft_username, party_id)
                VALUES (?, ?, ?)
            ''', (telegram_id, minecraft_username, party_id))
            self.db.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_party_applications(self, party_id: int) -> List[Dict]:
        """Получить все заявки партии"""
        cursor = self.db.execute('''
            SELECT * FROM party_applications 
            WHERE party_id = ? AND status = 'pending'
            ORDER BY applied_at ASC
        ''', (party_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_application_by_id(self, app_id: int) -> Optional[Dict]:
        """Получить заявку по ID"""
        cursor = self.db.execute('SELECT * FROM party_applications WHERE id = ?', (app_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def approve_application(self, application_id: int) -> bool:
        """Одобрить заявку на вступление"""
        cursor = self.db.execute('''
            SELECT telegram_id, minecraft_username, party_id 
            FROM party_applications WHERE id = ?
        ''', (application_id,))
        app = cursor.fetchone()
        
        if not app:
            return False
        
        telegram_id, minecraft_username, party_id = app
        
        # Получаем текущее количество членов
        cursor = self.db.execute('''
            SELECT COUNT(*) FROM party_members WHERE party_id = ?
        ''', (party_id,))
        count = cursor.fetchone()[0]
        
        # Добавляем в партию
        self.db.execute('''
            INSERT INTO party_members (telegram_id, minecraft_username, party_id, list_position)
            VALUES (?, ?, ?, ?)
        ''', (telegram_id, minecraft_username, party_id, count + 1))
        
        # Обновляем заявку
        self.db.execute('''
            UPDATE party_applications SET status = 'approved' WHERE id = ?
        ''', (application_id,))
        
        # Обновляем счётчик
        self.db.execute('''
            UPDATE parties SET members_count = members_count + 1 WHERE id = ?
        ''', (party_id,))
        
        self.db.commit()
        return True
    
    def reject_application(self, application_id: int) -> bool:
        """Отклонить заявку"""
        self.db.execute('''
            UPDATE party_applications SET status = 'rejected' WHERE id = ?
        ''', (application_id,))
        self.db.commit()
        return True
    
    def get_party_members(self, party_id: int) -> List[Dict]:
        """Получить всех членов партии"""
        cursor = self.db.execute('''
            SELECT * FROM party_members 
            WHERE party_id = ? 
            ORDER BY list_position ASC
        ''', (party_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def leave_party(self, telegram_id: int, party_id: int) -> bool:
        """Выйти из партии"""
        self.db.execute('''
            DELETE FROM party_members WHERE telegram_id = ? AND party_id = ?
        ''', (telegram_id, party_id))
        
        self.db.execute('''
            UPDATE parties SET members_count = members_count - 1 WHERE id = ?
        ''', (party_id,))
        
        self.db.commit()
        return True
    
    def delete_party(self, party_id: int) -> bool:
        """Удалить партию"""
        self.db.execute('DELETE FROM parties WHERE id = ?', (party_id,))
        self.db.commit()
        return True
    
    def transfer_leadership(self, party_id: int, new_leader_id: int) -> bool:
        """Передать лидерство"""
        # Снять роль лидера у старого
        self.db.execute('''
            UPDATE party_members SET role = 'member' WHERE party_id = ? AND role = 'leader'
        ''', (party_id,))
        
        # Назначить нового
        self.db.execute('''
            UPDATE party_members SET role = 'leader' WHERE telegram_id = ? AND party_id = ?
        ''', (new_leader_id, party_id))
        
        # Обновить в таблице партий
        self.db.execute('''
            UPDATE parties SET leader_telegram_id = ? WHERE id = ?
        ''', (new_leader_id, party_id))
        
        self.db.commit()
        return True
    
    def get_all_registered_parties(self) -> List[Dict]:
        """Получить все зарегистрированные партии"""
        cursor = self.db.execute('''
            SELECT * FROM parties WHERE registered = 1 ORDER BY members_count DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== ПАРЛАМЕНТ ==========
    
    def is_deputy(self, telegram_id: int) -> bool:
        """Проверить является ли игрок депутатом"""
        cursor = self.db.execute('''
            SELECT 1 FROM parliament WHERE telegram_id = ? AND term_end > datetime('now')
        ''', (telegram_id,))
        return cursor.fetchone() is not None
    
    def get_parliament_members(self) -> List[Dict]:
        """Получить всех текущих депутатов"""
        cursor = self.db.execute('''
            SELECT p.*, pm.party_id, parties.name as party_name
            FROM parliament p
            LEFT JOIN party_members pm ON p.telegram_id = pm.telegram_id
            LEFT JOIN parties ON pm.party_id = parties.id
            WHERE p.term_end > datetime('now')
            ORDER BY parties.name, p.minecraft_username
        ''')
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Закрыть соединение с БД"""
        self.db.close()


# Глобальный экземпляр
db = PoliticsDatabase()
