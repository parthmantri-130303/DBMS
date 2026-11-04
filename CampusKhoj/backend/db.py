import logging
from contextlib import contextmanager
from typing import Any

import mysql.connector
from mysql.connector import pooling

from .config import config

logger = logging.getLogger(__name__)

_pool: pooling.MySQLConnectionPool | None = None

def init_db_pool():
    global _pool
    if _pool is not None:
        return _pool
    try:
        _pool = pooling.MySQLConnectionPool(
            pool_name="campuskhoj_pool",
            pool_size=config.DB_POOL_SIZE,
            pool_reset_session=True,
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            charset="utf8mb4",
            autocommit=False
        )
        logger.info(f"MySQL connection pool initialized with size {config.DB_POOL_SIZE}")
        return _pool
    except Exception as e:
        logger.warning(f"Could not connect to MySQL server ({e}).")
        return None

def get_connection():
    global _pool
    if _pool is None:
        init_db_pool()
    if _pool is not None:
        return _pool.get_connection()
    # Direct connection attempt as fallback
    return mysql.connector.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        charset="utf8mb4",
        autocommit=False
    )

@contextmanager
def get_db():
    """Provides a database connection with automatic return to pool."""
    conn = get_connection()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception as err:
            logger.debug(f"Error closing connection: {err}")

@contextmanager
def transaction():
    """Transaction context manager ensuring commit or rollback."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            conn.close()
        except Exception as err:
            logger.debug(f"Error closing connection: {err}")

def query_one(sql: str, params: tuple | list | dict = (), dictionary: bool = True) -> dict[str, Any] | None:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=dictionary)
        try:
            cursor.execute(sql, params)
            return cursor.fetchone()
        finally:
            cursor.close()

def query_all(sql: str, params: tuple | list | dict = (), dictionary: bool = True) -> list[dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.cursor(dictionary=dictionary)
        try:
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()

def execute(sql: str, params: tuple | list | dict = (), commit: bool = True) -> int:
    """Executes an INSERT/UPDATE/DELETE query and returns lastrowid or rowcount."""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params)
            if commit:
                conn.commit()
            return cursor.lastrowid or cursor.rowcount
        finally:
            cursor.close()

