"""Small DB-API adapter for the application's parameterized SQL queries."""
import json
from pathlib import Path
import pymysql

class Row(dict):
    def __getitem__(self, key):
        return tuple(self.values())[key] if isinstance(key, int) else super().__getitem__(key)

class Cursor:
    def __init__(self, cursor): self.cursor = cursor
    def fetchone(self):
        row = self.cursor.fetchone()
        return Row(row) if row is not None else None
    def fetchall(self): return [Row(row) for row in self.cursor.fetchall()]
    def __iter__(self): return iter(self.fetchall())
    @property
    def rowcount(self): return self.cursor.rowcount
    @property
    def lastrowid(self): return self.cursor.lastrowid

class Connection:
    def __init__(self, config_path):
        config = json.loads(Path(config_path).read_text())
        self.db = pymysql.connect(**config, charset='utf8mb4', autocommit=False,
                                  cursorclass=pymysql.cursors.DictCursor,
                                  connect_timeout=5, read_timeout=15, write_timeout=15)
    @staticmethod
    def sql(sql):
        return sql.replace('?', '%s').replace('INSERT OR IGNORE', 'INSERT IGNORE').replace("s.owner_id='user:'||u.id", "s.owner_id=CONCAT('user:',u.id)")
    def execute(self, sql, params=()):
        cursor = self.db.cursor()
        if sql == 'BEGIN IMMEDIATE':
            self.db.begin()
            cursor.execute("SELECT name FROM app_locks WHERE name='auth_write' FOR UPDATE")
        else: cursor.execute(self.sql(sql), params)
        return Cursor(cursor)
    def executemany(self, sql, rows):
        cursor = self.db.cursor()
        cursor.executemany(self.sql(sql), rows)
        return Cursor(cursor)
    def commit(self): self.db.commit()
    def rollback(self): self.db.rollback()
    def close(self): self.db.close()
