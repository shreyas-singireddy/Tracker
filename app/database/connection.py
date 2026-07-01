import sqlite3
import threading
from contextlib import contextmanager
from typing import Any

from app.core.config import settings
from app.core.exceptions import DatabaseError
from app.core.logging import logger


class DatabaseManager:
    """Thread-safe SQLite connection manager with WAL mode and foreign key enforcement."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(settings.DB_PATH)
        self._thread_local = threading.local()
        logger.info(f"DatabaseManager initialized for database at: {self.db_path}")

    def _get_thread_connection(self) -> sqlite3.Connection:
        """Retrieves or creates a thread-local connection configured with performance pragmas."""
        if not hasattr(self._thread_local, "connection"):
            try:
                # check_same_thread=False allows sharing if we handle lock/sync,
                # but thread_local guarantees thread separation.
                conn = sqlite3.connect(
                    self.db_path,
                    timeout=10.0,  # 10s busy timeout for WAL concurrency
                    check_same_thread=False,
                )
                conn.row_factory = sqlite3.Row  # Returns rows as dictionary-like objects

                # Configure critical SQLite Pragmas
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys = ON;")
                cursor.execute("PRAGMA journal_mode = WAL;")
                cursor.execute("PRAGMA synchronous = NORMAL;")
                cursor.close()

                self._thread_local.connection = conn
                logger.debug("New thread-local SQLite connection initialized.")
            except sqlite3.Error as e:
                logger.error(f"Failed to connect to SQLite: {e!s}")
                raise DatabaseError("Failed to initialize database connection", details=str(e))

        return self._thread_local.connection

    @contextmanager
    def transaction(self):
        """Context manager to run transactions with automatic commit and rollback."""
        conn = self._get_thread_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            try:
                conn.rollback()
            except sqlite3.Error as rollback_err:
                logger.error(f"Transaction rollback failed: {rollback_err!s}")
            logger.error(f"Transaction failed, changes rolled back: {e!s}")
            raise DatabaseError("Transaction error, database rolled back", details=str(e))

    def execute_write(self, query: str, params: tuple = ()) -> int:
        """Executes a write query (INSERT, UPDATE, DELETE) and returns the ID of the last inserted row or number of affected rows."""
        with self.transaction() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(query, params)
                last_id = cursor.lastrowid
                row_count = cursor.rowcount
                cursor.close()
                # If it's an insert, return last inserted ID; otherwise, return affected rows.
                return last_id if last_id is not None and last_id > 0 else row_count
            except sqlite3.Error as e:
                logger.error(f"Database write execution failed: {e!s}\nQuery: {query}")
                raise DatabaseError("Failed to write to database", details=str(e))

    def execute_read(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Executes a read query (SELECT) and returns rows as a list of dictionaries."""
        conn = self._get_thread_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            cursor.close()
            return results
        except sqlite3.Error as e:
            logger.error(f"Database read execution failed: {e!s}\nQuery: {query}")
            raise DatabaseError("Failed to read from database", details=str(e))

    def execute_read_one(self, query: str, params: tuple = ()) -> dict[str, Any] | None:
        """Executes a read query (SELECT) and returns the first row or None."""
        results = self.execute_read(query, params)
        return results[0] if results else None

    def close_connection(self):
        """Closes the current thread's connection if it exists."""
        if hasattr(self._thread_local, "connection"):
            try:
                self._thread_local.connection.close()
                delattr(self._thread_local, "connection")
                logger.debug("Closed thread-local SQLite connection.")
            except sqlite3.Error as e:
                logger.warning(f"Error closing SQLite connection: {e!s}")


# Global Database Manager Instance
db_manager = DatabaseManager()
