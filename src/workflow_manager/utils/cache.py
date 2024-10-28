from pathlib import Path
from typing import List
import sqlite3
import json

class CacheManager:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database and create table if not exists"""
        if not self.file_path.parent.exists():
            self.file_path.parent.mkdir(parents=True)
            
        with sqlite3.connect(self.file_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS servers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data JSON,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def read_cache(self) -> List[dict]:
        """从SQLite数据库中读取服务器数据"""
        try:
            with sqlite3.connect(self.file_path) as conn:
                cursor = conn.execute("SELECT data FROM servers ORDER BY timestamp DESC LIMIT 1")
                row = cursor.fetchone()
                if row and row[0]:
                    return json.loads(row[0])
        except sqlite3.Error:
            # 如果发生错误，删除数据库文件
            if self.file_path.exists():
                self.file_path.unlink()
        return []

    def write_cache(self, data: List[dict]):
        """将服务器数据写入SQLite数据库"""
        with sqlite3.connect(self.file_path) as conn:
            # 先清除旧数据
            conn.execute("DELETE FROM servers")
            # 插入新数据
            conn.execute(
                "INSERT INTO servers (data) VALUES (?)",
                (json.dumps(data, ensure_ascii=False),)
            )
