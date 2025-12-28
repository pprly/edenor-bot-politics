"""
Модели базы данных SQLite
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import secrets

from config import DATABASE_PATH


class Database:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = DATABASE_PATH
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.init_db()
    
    def init_db(self):
        """Инициализация всех таблиц"""
        
        # Пользователи (верифицированные)
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                minecraft_username TEXT NOT NULL,
                verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_auth_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Партии
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS parties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                ideology TEXT,
                description TEXT,
                photo_file_id TEXT,
                leader_telegram_id INTEGER NOT NULL,
                invite_code TEXT UNIQUE,
                is_registered BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                registration_deadline TIMESTAMP,
                members_count INTEGER DEFAULT 1,
                FOREIGN KEY (leader_telegram_id) REFERENCES users(telegram_id)
            )
        ''')
        
        # Члены партий
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS party_members (
                telegram_id INTEGER,
                party_id INTEGER,
                role TEXT DEFAULT 'member',
                list_position INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (telegram_id, party_id),
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
                FOREIGN KEY (party_id) REFERENCES parties(id) ON DELETE CASCADE
            )
        ''')
        
        # Заявки на вступление в партию
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS party_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                party_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
                FOREIGN KEY (party_id) REFERENCES parties(id) ON DELETE CASCADE,
                UNIQUE(telegram_id, party_id)
            )
        ''')
        
        # Парламент
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS parliament (
                telegram_id INTEGER PRIMARY KEY,
                party_id INTEGER,
                term_start TIMESTAMP,
                term_end TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
                FOREIGN KEY (party_id) REFERENCES parties(id) ON DELETE SET NULL
            )
        ''')
        
        # Выборы в парламент
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS elections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT DEFAULT 'active',
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_date TIMESTAMP,
                channel_message_id INTEGER,
                results TEXT
            )
        ''')
        
        # Голоса на выборах
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS election_votes (
                election_id INTEGER,
                voter_telegram_id INTEGER,
                party_id INTEGER,
                voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (election_id, voter_telegram_id),
                FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
                FOREIGN KEY (voter_telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE,
                FOREIGN KEY (party_id) REFERENCES parties(id) ON DELETE CASCADE
            )
        ''')
        
        # Голосования (обычные и парламентские)
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS votings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                voting_type TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_by INTEGER,
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_date TIMESTAMP,
                channel_message_id INTEGER,
                votes_for INTEGER DEFAULT 0,
                votes_against INTEGER DEFAULT 0,
                FOREIGN KEY (created_by) REFERENCES users(telegram_id)
            )
        ''')
        
        # Голоса в голосованиях
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS voting_votes (
                voting_id INTEGER,
                voter_telegram_id INTEGER,
                vote TEXT,
                voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (voting_id, voter_telegram_id),
                FOREIGN KEY (voting_id) REFERENCES votings(id) ON DELETE CASCADE,
                FOREIGN KEY (voter_telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
            )
        ''')
        
        # Логи действий
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS action_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        ''')
        
        self.db.commit()
    
    # ========== ПОЛЬЗОВАТЕЛИ ==========
    
    def add_user(self, telegram_id: int, minecraft_username: str) -> bool:
        """Добавить верифицированного пользователя"""
        try:
            self.db.execute('''
                INSERT OR REPLACE INTO users (telegram_id, minecraft_username, verified_at, last_auth_check)
                VALUES (?, ?, ?, ?)
            ''', (telegram_id, minecraft_username, datetime.now(), datetime.now()))
            self.db.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Получить пользователя по telegram_id"""
        cursor = self.db.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_auth_check(self, telegram_id: int) -> bool:
        """Обновить время последней проверки авторизации"""
        self.db.execute('''
            UPDATE users SET last_auth_check = ? WHERE telegram_id = ?
        ''', (datetime.now(), telegram_id))
        self.db.commit()
        return True
    
    def get_users_for_auth_recheck(self, days: int) -> List[Dict]:
        """Получить пользователей для переавторизации"""
        cursor = self.db.execute('''
            SELECT * FROM users 
            WHERE last_auth_check < datetime('now', '-' || ? || ' days')
            AND is_active = 1
        ''', (days,))
        return [dict(row) for row in cursor.fetchall()]
    
    def deactivate_user(self, telegram_id: int) -> bool:
        """Деактивировать пользователя"""
        self.db.execute('UPDATE users SET is_active = 0 WHERE telegram_id = ?', (telegram_id,))
        self.db.commit()
        return True
    
    # ========== ПАРТИИ ==========
    
    def create_party(self, name: str, ideology: str, description: str,
                    leader_telegram_id: int, deadline_minutes: int) -> Tuple[int, str]:
        """Создать партию с кодом приглашения"""
        invite_code = secrets.token_urlsafe(8)
        deadline = datetime.now() + timedelta(minutes=deadline_minutes)
        
        cursor = self.db.execute('''
            INSERT INTO parties (name, ideology, description, leader_telegram_id, 
                               invite_code, registration_deadline)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, ideology, description, leader_telegram_id, invite_code, deadline))
        
        party_id = cursor.lastrowid
        
        # Добавляем создателя как главу
        self.db.execute('''
            INSERT INTO party_members (telegram_id, party_id, role, list_position)
            VALUES (?, ?, 'leader', 1)
        ''', (leader_telegram_id, party_id))
        
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
    
    def get_all_parties(self, registered_only: bool = False) -> List[Dict]:
        """Получить все партии"""
        query = 'SELECT * FROM parties'
        if registered_only:
            query += ' WHERE is_registered = 1'
        query += ' ORDER BY members_count DESC'
        
        cursor = self.db.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    
    def update_party_name(self, party_id: int, new_name: str) -> bool:
        """Изменить название партии"""
        try:
            self.db.execute('UPDATE parties SET name = ? WHERE id = ?', (new_name, party_id))
            self.db.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def set_party_photo(self, party_id: int, photo_file_id: str) -> bool:
        """Установить фото партии"""
        self.db.execute('UPDATE parties SET photo_file_id = ? WHERE id = ?', (photo_file_id, party_id))
        self.db.commit()
        return True
    
    def register_party(self, party_id: int) -> bool:
        """Зарегистрировать партию (набран минимум членов)"""
        self.db.execute('UPDATE parties SET is_registered = 1 WHERE id = ?', (party_id,))
        self.db.commit()
        return True
    
    def delete_party(self, party_id: int) -> bool:
        """Удалить партию"""
        self.db.execute('DELETE FROM parties WHERE id = ?', (party_id,))
        self.db.commit()
        return True
    
    # ========== ЧЛЕНЫ ПАРТИЙ ==========
    
    def apply_to_party(self, telegram_id: int, party_id: int) -> bool:
        """Подать заявку на вступление"""
        try:
            self.db.execute('''
                INSERT INTO party_applications (telegram_id, party_id)
                VALUES (?, ?)
            ''', (telegram_id, party_id))
            self.db.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_party_applications(self, party_id: int, status: str = 'pending') -> List[Dict]:
        """Получить заявки партии"""
        cursor = self.db.execute('''
            SELECT pa.*, u.minecraft_username 
            FROM party_applications pa
            JOIN users u ON pa.telegram_id = u.telegram_id
            WHERE pa.party_id = ? AND pa.status = ?
            ORDER BY pa.applied_at ASC
        ''', (party_id, status))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_application_by_id(self, app_id: int) -> Optional[Dict]:
        """Получить заявку по ID"""
        cursor = self.db.execute('''
            SELECT pa.*, u.minecraft_username 
            FROM party_applications pa
            JOIN users u ON pa.telegram_id = u.telegram_id
            WHERE pa.id = ?
        ''', (app_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def approve_application(self, application_id: int) -> bool:
        """Одобрить заявку"""
        cursor = self.db.execute('''
            SELECT telegram_id, party_id FROM party_applications WHERE id = ?
        ''', (application_id,))
        app = cursor.fetchone()
        
        if not app:
            return False
        
        telegram_id, party_id = app
        
        # Получаем текущее количество членов
        cursor = self.db.execute('''
            SELECT COUNT(*) FROM party_members WHERE party_id = ?
        ''', (party_id,))
        count = cursor.fetchone()[0]
        
        # Добавляем в партию
        self.db.execute('''
            INSERT INTO party_members (telegram_id, party_id, list_position)
            VALUES (?, ?, ?)
        ''', (telegram_id, party_id, count + 1))
        
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
            SELECT pm.*, u.minecraft_username 
            FROM party_members pm
            JOIN users u ON pm.telegram_id = u.telegram_id
            WHERE pm.party_id = ? 
            ORDER BY pm.list_position ASC
        ''', (party_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_member_info(self, telegram_id: int, party_id: int) -> Optional[Dict]:
        """Получить информацию о члене партии"""
        cursor = self.db.execute('''
            SELECT pm.*, u.minecraft_username 
            FROM party_members pm
            JOIN users u ON pm.telegram_id = u.telegram_id
            WHERE pm.telegram_id = ? AND pm.party_id = ?
        ''', (telegram_id, party_id))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def remove_member(self, telegram_id: int, party_id: int) -> bool:
        """Удалить участника из партии"""
        self.db.execute('''
            DELETE FROM party_members WHERE telegram_id = ? AND party_id = ?
        ''', (telegram_id, party_id))
        
        self.db.execute('''
            UPDATE parties SET members_count = members_count - 1 WHERE id = ?
        ''', (party_id,))
        
        self.db.commit()
        return True
    
    def transfer_leadership(self, party_id: int, new_leader_id: int) -> bool:
        """Передать лидерство"""
        # Снять роль лидера у старого
        self.db.execute('''
            UPDATE party_members SET role = 'member' 
            WHERE party_id = ? AND role = 'leader'
        ''', (party_id,))
        
        # Назначить нового
        self.db.execute('''
            UPDATE party_members SET role = 'leader' 
            WHERE telegram_id = ? AND party_id = ?
        ''', (new_leader_id, party_id))
        
        # Обновить в таблице партий
        self.db.execute('''
            UPDATE parties SET leader_telegram_id = ? WHERE id = ?
        ''', (new_leader_id, party_id))
        
        self.db.commit()
        return True
    
    def swap_member_positions(self, party_id: int, pos1: int, pos2: int) -> bool:
        """Поменять местами участников в списке"""
        self.db.execute('''
            UPDATE party_members SET list_position = 
            CASE 
                WHEN list_position = ? THEN ?
                WHEN list_position = ? THEN ?
            END
            WHERE party_id = ? AND list_position IN (?, ?)
        ''', (pos1, pos2, pos2, pos1, party_id, pos1, pos2))
        self.db.commit()
        return True
    
    # ========== ПАРЛАМЕНТ ==========
    
    def clear_parliament(self) -> bool:
        """Распустить парламент"""
        self.db.execute('DELETE FROM parliament')
        self.db.commit()
        return True
    
    def add_to_parliament(self, telegram_id: int, party_id: int, term_months: int = 6) -> bool:
        """Добавить депутата в парламент"""
        term_start = datetime.now()
        term_end = term_start + timedelta(days=term_months * 30)
        
        self.db.execute('''
            INSERT INTO parliament (telegram_id, party_id, term_start, term_end)
            VALUES (?, ?, ?, ?)
        ''', (telegram_id, party_id, term_start, term_end))
        self.db.commit()
        return True
    
    def get_parliament_members(self) -> List[Dict]:
        """Получить всех депутатов"""
        cursor = self.db.execute('''
            SELECT p.*, u.minecraft_username, parties.name as party_name
            FROM parliament p
            JOIN users u ON p.telegram_id = u.telegram_id
            LEFT JOIN parties ON p.party_id = parties.id
            ORDER BY parties.name, u.minecraft_username
        ''')
        return [dict(row) for row in cursor.fetchall()]
    
    def is_deputy(self, telegram_id: int) -> bool:
        """Проверить является ли депутатом"""
        cursor = self.db.execute('''
            SELECT 1 FROM parliament WHERE telegram_id = ?
        ''', (telegram_id,))
        return cursor.fetchone() is not None
    
    def get_parliament_count(self) -> int:
        """Получить количество депутатов"""
        cursor = self.db.execute('SELECT COUNT(*) FROM parliament')
        return cursor.fetchone()[0]
    
    # ========== ВЫБОРЫ ==========
    
    def create_election(self, end_date: datetime) -> int:
        """Создать выборы"""
        cursor = self.db.execute('''
            INSERT INTO elections (end_date) VALUES (?)
        ''', (end_date,))
        election_id = cursor.lastrowid
        self.db.commit()
        return election_id
    
    def get_election_by_id(self, election_id: int) -> Optional[Dict]:
        """Получить выборы по ID"""
        cursor = self.db.execute('SELECT * FROM elections WHERE id = ?', (election_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_active_election(self) -> Optional[Dict]:
        """Получить активные выборы"""
        cursor = self.db.execute('''
            SELECT * FROM elections WHERE status = 'active' 
            ORDER BY start_date DESC LIMIT 1
        ''')
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def vote_in_election(self, election_id: int, voter_id: int, party_id: int) -> bool:
        """Проголосовать на выборах"""
        try:
            self.db.execute('''
                INSERT INTO election_votes (election_id, voter_telegram_id, party_id)
                VALUES (?, ?, ?)
            ''', (election_id, voter_id, party_id))
            self.db.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_election_results(self, election_id: int) -> List[Dict]:
        """Получить результаты выборов"""
        cursor = self.db.execute('''
            SELECT p.id, p.name, COUNT(ev.voter_telegram_id) as votes
            FROM parties p
            LEFT JOIN election_votes ev ON p.id = ev.party_id AND ev.election_id = ?
            WHERE p.is_registered = 1
            GROUP BY p.id
            ORDER BY votes DESC
        ''', (election_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_election_total_votes(self, election_id: int) -> int:
        """Получить общее количество голосов"""
        cursor = self.db.execute('''
            SELECT COUNT(*) FROM election_votes WHERE election_id = ?
        ''', (election_id,))
        return cursor.fetchone()[0]
    
    def has_voted_in_election(self, election_id: int, telegram_id: int) -> bool:
        """Проверить проголосовал ли"""
        cursor = self.db.execute('''
            SELECT 1 FROM election_votes 
            WHERE election_id = ? AND voter_telegram_id = ?
        ''', (election_id, telegram_id))
        return cursor.fetchone() is not None
    
    def close_election(self, election_id: int, results: str) -> bool:
        """Закрыть выборы"""
        self.db.execute('''
            UPDATE elections SET status = 'closed', results = ? WHERE id = ?
        ''', (results, election_id))
        self.db.commit()
        return True
    
    def set_election_channel_message(self, election_id: int, message_id: int) -> bool:
        """Установить ID сообщения в канале"""
        self.db.execute('''
            UPDATE elections SET channel_message_id = ? WHERE id = ?
        ''', (message_id, election_id))
        self.db.commit()
        return True
    
    # ========== ГОЛОСОВАНИЯ ==========
    
    def create_voting(self, title: str, description: str, voting_type: str,
                     created_by: int, end_date: datetime) -> int:
        """Создать голосование"""
        cursor = self.db.execute('''
            INSERT INTO votings (title, description, voting_type, created_by, end_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, description, voting_type, created_by, end_date))
        voting_id = cursor.lastrowid
        self.db.commit()
        return voting_id
    
    def get_voting_by_id(self, voting_id: int) -> Optional[Dict]:
        """Получить голосование по ID"""
        cursor = self.db.execute('SELECT * FROM votings WHERE id = ?', (voting_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_active_votings(self) -> List[Dict]:
        """Получить все активные голосования"""
        cursor = self.db.execute('''
            SELECT * FROM votings WHERE status = 'active' 
            ORDER BY start_date DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]
    
    def vote(self, voting_id: int, voter_id: int, vote: str) -> bool:
        """Проголосовать"""
        try:
            self.db.execute('''
                INSERT INTO voting_votes (voting_id, voter_telegram_id, vote)
                VALUES (?, ?, ?)
            ''', (voting_id, voter_id, vote))
            
            # Обновляем счётчики
            if vote == 'for':
                self.db.execute('UPDATE votings SET votes_for = votes_for + 1 WHERE id = ?', (voting_id,))
            elif vote == 'against':
                self.db.execute('UPDATE votings SET votes_against = votes_against + 1 WHERE id = ?', (voting_id,))
            
            self.db.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def has_voted(self, voting_id: int, telegram_id: int) -> bool:
        """Проверить проголосовал ли"""
        cursor = self.db.execute('''
            SELECT 1 FROM voting_votes 
            WHERE voting_id = ? AND voter_telegram_id = ?
        ''', (voting_id, telegram_id))
        return cursor.fetchone() is not None
    
    def get_voting_results(self, voting_id: int) -> List[Dict]:
        """Получить детальные результаты голосования"""
        cursor = self.db.execute('''
            SELECT vv.*, u.minecraft_username 
            FROM voting_votes vv
            JOIN users u ON vv.voter_telegram_id = u.telegram_id
            WHERE vv.voting_id = ?
            ORDER BY vv.voted_at ASC
        ''', (voting_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def close_voting(self, voting_id: int) -> bool:
        """Закрыть голосование"""
        self.db.execute("UPDATE votings SET status = 'closed' WHERE id = ?", (voting_id,))
        self.db.commit()
        return True
    
    def set_voting_channel_message(self, voting_id: int, message_id: int) -> bool:
        """Установить ID сообщения в канале"""
        self.db.execute('''
            UPDATE votings SET channel_message_id = ? WHERE id = ?
        ''', (message_id, voting_id))
        self.db.commit()
        return True
    
    # ========== ЛОГИ ==========
    
    def log_action(self, telegram_id: int, action: str, details: str = None):
        """Записать действие в лог"""
        self.db.execute('''
            INSERT INTO action_logs (telegram_id, action, details)
            VALUES (?, ?, ?)
        ''', (telegram_id, action, details))
        self.db.commit()
    
    def get_logs(self, limit: int = 100) -> List[Dict]:
        """Получить последние логи"""
        cursor = self.db.execute('''
            SELECT al.*, u.minecraft_username 
            FROM action_logs al
            LEFT JOIN users u ON al.telegram_id = u.telegram_id
            ORDER BY al.created_at DESC LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Закрыть соединение"""
        self.db.close()


# Глобальный экземпляр
db = Database()