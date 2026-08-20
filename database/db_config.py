"""MySQL connection pool for DELTA."""

import mysql.connector
from mysql.connector import pooling
import yaml
import os

_pool = None


def _load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config.get('mysql', {})


def get_pool():
    global _pool
    if _pool is None:
        cfg = _load_config()
        _pool = pooling.MySQLConnectionPool(
            pool_name="delta_pool",
            pool_size=5,
            pool_reset_session=True,
            host=cfg.get('host', 'localhost'),
            port=cfg.get('port', 3306),
            user=cfg.get('user', 'delta'),
            password=cfg.get('password', ''),
            database=cfg.get('database', 'delta'),
            autocommit=False
        )
    return _pool


def get_connection():
    return get_pool().get_connection()


class DBConnection:
    """Context manager for database transactions."""

    def __init__(self):
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor(dictionary=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.cursor.close()
        self.conn.close()
        return False

    def execute(self, query, params=None):
        self.cursor.execute(query, params or ())
        return self.cursor

    def executemany(self, query, params_list):
        self.cursor.executemany(query, params_list)
        return self.cursor

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    @property
    def lastrowid(self):
        return self.cursor.lastrowid


def init_db():
    """Create tables from schema.sql."""
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r') as f:
        sql = f.read()

    conn = get_connection()
    cursor = conn.cursor()
    for statement in sql.split(';'):
        stmt = statement.strip()
        if stmt and not stmt.startswith('--'):
            cursor.execute(stmt)
    conn.commit()
    cursor.close()
    conn.close()
    print("Database tables initialized.")
