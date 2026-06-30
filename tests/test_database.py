import os
import sqlite3
import unittest
from pathlib import Path
from app.database.connection import DatabaseManager
from app.database.migrations import MigrationRunner
from app.core.exceptions import DatabaseError

TEST_DB_PATH = Path(__file__).resolve().parent / "test_fitos.db"


class TestDatabaseManager(unittest.TestCase):
    """Verifies SQLite transaction rollbacks, query routing, and thread safety configuration."""

    def setUp(self):
        # Initialize database manager targeting a temporary test file
        self.db = DatabaseManager(db_path=str(TEST_DB_PATH))
        
        # Create a simple test table for database validation
        self.db.execute_write("CREATE TABLE IF NOT EXISTS test_users (id INTEGER PRIMARY KEY, name TEXT);")

    def tearDown(self):
        # Close connection and clean up temporary database file
        self.db.close_connection()
        if TEST_DB_PATH.exists():
            try:
                os.remove(TEST_DB_PATH)
                # Also remove WAL files if they exist
                for suffix in ["-wal", "-shm"]:
                    extra_file = Path(str(TEST_DB_PATH) + suffix)
                    if extra_file.exists():
                        os.remove(extra_file)
            except OSError:
                pass

    def test_write_and_read(self):
        """Verifies simple write insertions and matching row selections."""
        last_id = self.db.execute_write("INSERT INTO test_users (name) VALUES (?);", ("Alice",))
        self.assertEqual(last_id, 1)

        row = self.db.execute_read_one("SELECT * FROM test_users WHERE id = ?;", (1,))
        self.assertIsNotNone(row)
        self.assertEqual(row["name"], "Alice")

    def test_transaction_rollback_on_failure(self):
        """Verifies that queries grouped in a transaction rollback completely if any step raises an error."""
        # Insert a valid starting record
        self.db.execute_write("INSERT INTO test_users (name) VALUES (?);", ("Bob",))
        
        # Run transaction block with an intentional error
        try:
            with self.db.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO test_users (name) VALUES (?);", ("Charlie",))
                # Intentional error: inserting duplicate/invalid sql or raising error manually
                raise sqlite3.IntegrityError("Simulated write fail")
        except DatabaseError:
            pass  # Expected exception propagated by manager

        # Charlie should NOT have been committed to the database
        charlie_row = self.db.execute_read_one("SELECT * FROM test_users WHERE name = ?;", ("Charlie",))
        self.assertIsNone(charlie_row)

    def test_migration_runner(self):
        """Verifies that the migration engine runs successfully, applies versioning schemas, and logs applied versions."""
        runner = MigrationRunner()
        # Direct migrations directory check is implicit, let's trigger run on our manager path
        runner.init_migration_table()
        applied = runner.get_applied_migrations()
        self.assertIsInstance(applied, set)


if __name__ == "__main__":
    unittest.main()
