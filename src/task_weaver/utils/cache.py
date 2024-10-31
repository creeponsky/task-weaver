import json
import sqlite3
from enum import Enum, auto
from pathlib import Path
from typing import Any
from ..log.logger import logger

class CacheType(Enum):
    SERVER = auto()
    TASK = auto()
    PROGRAM = auto()

class CacheManager:
    def __init__(self, db_name: str, cache_type: CacheType):
        if not isinstance(cache_type, CacheType):
            raise ValueError("cache_type must be a CacheType enum")
        if not db_name or not isinstance(db_name, str):
            raise ValueError("db_name must be a non-empty string")
            
        self.cache_type = cache_type
        cache_dir = Path("caches")
        self.file_path = cache_dir / f"{db_name}.db"
        try:
            self._init_db()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _init_db(self):
        """Initialize SQLite database and create table if not exists"""
        try:
            if not self.file_path.parent.exists():
                self.file_path.parent.mkdir(parents=True)
                
            # Determine table schema based on cache type
            if self.cache_type == CacheType.SERVER:
                self._create_server_table()
            elif self.cache_type == CacheType.TASK:
                self._create_task_table()
            elif self.cache_type == CacheType.PROGRAM:
                self._create_program_table()
        except PermissionError as e:
            logger.error(f"Permission denied when creating cache directory: {e}")
            raise
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def _create_server_table(self):
        try:
            with sqlite3.connect(self.file_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS servers (
                        server_name TEXT PRIMARY KEY,
                        data JSON,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
        except sqlite3.Error as e:
            logger.error(f"Error creating server table: {e}")
            raise

    def _create_task_table(self):
        try:
            with sqlite3.connect(self.file_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY,
                        data JSON,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
        except sqlite3.Error as e:
            logger.error(f"Error creating task table: {e}")
            raise

    def _create_program_table(self):
        try:
            with sqlite3.connect(self.file_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS program_info (
                        id INTEGER PRIMARY KEY,
                        data JSON,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
        except sqlite3.Error as e:
            logger.error(f"Error creating program table: {e}")
            raise

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
            logger.error(f"Database error during read: {e}")
            if self.file_path.exists():
                try:
                    self.file_path.unlink()
                except Exception as e:
                    logger.error(f"Failed to delete corrupted database: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON data in cache: {e}")
        except Exception as e:
            logger.error(f"Unexpected error reading cache: {e}")
        return [] if self.cache_type != CacheType.PROGRAM else {}

    def write_cache(self, data: Any):
        """Write data to cache based on cache type"""
        if not isinstance(data, (list, dict)):
            raise ValueError("Data must be a list or dictionary")
            
        try:
            with sqlite3.connect(self.file_path) as conn:
                if self.cache_type == CacheType.SERVER:
                    if not isinstance(data, list):
                        raise ValueError("Server cache data must be a list")
                    conn.execute("DELETE FROM servers")
                    for server in data:
                        if not isinstance(server, dict):
                            raise ValueError("Each server entry must be a dictionary")
                        conn.execute(
                            "INSERT INTO servers (server_name, data) VALUES (?, ?)",
                            (server.get('server_name', ''), json.dumps(server))
                        )
                
                elif self.cache_type == CacheType.TASK:
                    if not isinstance(data, list):
                        raise ValueError("Task cache data must be a list")
                    for task in data:
                        if not isinstance(task, dict) or 'task_id' not in task or 'data' not in task:
                            raise ValueError("Invalid task data format")
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO tasks (task_id, data) 
                            VALUES (?, ?)
                            """,
                            (task['task_id'], task['data'])
                        )
                
                elif self.cache_type == CacheType.PROGRAM:
                    if not isinstance(data, dict):
                        raise ValueError("Program cache data must be a dictionary")
                    conn.execute("DELETE FROM program_info")
                    conn.execute(
                        "INSERT INTO program_info (data) VALUES (?)",
                        (json.dumps(data),)
                    )
        except sqlite3.Error as e:
            logger.error(f"Database error during write: {e}")
            raise
        except json.JSONEncodeError as e:
            logger.error(f"Failed to encode data as JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error writing cache: {e}")
            raise
