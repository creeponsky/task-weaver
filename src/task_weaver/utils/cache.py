from pathlib import Path
from typing import List, Dict, Any
import sqlite3
import json
from enum import Enum, auto

class CacheType(Enum):
    SERVER = auto()
    TASK = auto()
    PROGRAM = auto()

class CacheManager:
    def __init__(self, db_name: str, cache_type: CacheType):
        self.cache_type = cache_type
        cache_dir = Path("caches")
        self.file_path = cache_dir / f"{db_name}.db"
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database and create table if not exists"""
        if not self.file_path.parent.exists():
            self.file_path.parent.mkdir(parents=True)
            
        # Determine table schema based on cache type
        if self.cache_type == CacheType.SERVER:
            self._create_server_table()
        elif self.cache_type == CacheType.TASK:
            self._create_task_table()
        elif self.cache_type == CacheType.PROGRAM:
            self._create_program_table()

    def _create_server_table(self):
        with sqlite3.connect(self.file_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS servers (
                    server_name TEXT PRIMARY KEY,
                    data JSON,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def _create_task_table(self):
        with sqlite3.connect(self.file_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    data JSON,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def _create_program_table(self):
        with sqlite3.connect(self.file_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS program_info (
                    id INTEGER PRIMARY KEY,
                    data JSON,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def read_cache(self) -> Any:
        """Read data from cache based on cache type"""
        try:
            with sqlite3.connect(self.file_path) as conn:
                if self.cache_type == CacheType.SERVER:
                    cursor = conn.execute("SELECT data FROM servers")
                    rows = cursor.fetchall()
                    return [json.loads(row[0]) for row in rows] if rows else []
                
                elif self.cache_type == CacheType.TASK:
                    cursor = conn.execute("SELECT data FROM tasks")
                    rows = cursor.fetchall()
                    return [{'task_id': json.loads(row[0])['task_id'], 'data': row[0]} for row in rows]
                
                elif self.cache_type == CacheType.PROGRAM:
                    cursor = conn.execute("SELECT data FROM program_info ORDER BY timestamp DESC LIMIT 1")
                    row = cursor.fetchone()
                    return json.loads(row[0]) if row else {}
                
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            if self.file_path.exists():
                self.file_path.unlink()
        return [] if self.cache_type != CacheType.PROGRAM else {}

    def write_cache(self, data: Any):
        """Write data to cache based on cache type"""
        with sqlite3.connect(self.file_path) as conn:
            if self.cache_type == CacheType.SERVER:
                conn.execute("DELETE FROM servers")
                for server in data:
                    conn.execute(
                        "INSERT INTO servers (server_name, data) VALUES (?, ?)",
                        (server.get('server_name', ''), json.dumps(server))
                    )
            
            elif self.cache_type == CacheType.TASK:
                for task in data:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO tasks (task_id, data) 
                        VALUES (?, ?)
                        """,
                        (task['task_id'], task['data'])
                    )
            
            elif self.cache_type == CacheType.PROGRAM:
                conn.execute("DELETE FROM program_info")
                conn.execute(
                    "INSERT INTO program_info (data) VALUES (?)",
                    (json.dumps(data),)
                )
