import os
import unittest
from pathlib import Path
from app.database.connection import DatabaseManager
from app.repositories.base import BaseRepository
from app.core.exceptions import RepositoryError

TEST_REPO_DB_PATH = Path(__file__).resolve().parent / "test_fitos_repo.db"


class TestBaseRepository(unittest.TestCase):
    """Verifies that the generic BaseRepository correctly implements parameterized queries for CRUD."""

    def setUp(self):
        self.db = DatabaseManager(db_path=str(TEST_REPO_DB_PATH))
        self.repo = BaseRepository(db=self.db)
        
        # Initialize schema table
        self.db.execute_write(
            "CREATE TABLE IF NOT EXISTS test_items (item_id TEXT PRIMARY KEY, title TEXT, quantity INTEGER);"
        )

    def tearDown(self):
        self.db.close_connection()
        if TEST_REPO_DB_PATH.exists():
            try:
                os.remove(TEST_REPO_DB_PATH)
                for suffix in ["-wal", "-shm"]:
                    extra_file = Path(str(TEST_REPO_DB_PATH) + suffix)
                    if extra_file.exists():
                        os.remove(extra_file)
            except OSError:
                pass

    def test_crud_lifecycle(self):
        """Verifies the complete creation, retrieval, updating, and deletion cycle."""
        
        # 1. Create (Insert)
        item_data = {"item_id": "itm-01", "title": "Resistance Band", "quantity": 5}
        self.repo.create("test_items", item_data)
        
        # 2. Read (Select Single)
        row = self.repo.read("test_items", "item_id", "itm-01")
        self.assertIsNotNone(row)
        self.assertEqual(row["title"], "Resistance Band")
        self.assertEqual(row["quantity"], 5)

        # 3. Update
        self.repo.update("test_items", "item_id", "itm-01", {"quantity": 8, "title": "Loop Band"})
        updated_row = self.repo.read("test_items", "item_id", "itm-01")
        self.assertEqual(updated_row["quantity"], 8)
        self.assertEqual(updated_row["title"], "Loop Band")

        # 4. List All
        all_items = self.repo.list_all("test_items")
        self.assertEqual(len(all_items), 1)

        # 5. Delete
        self.repo.delete("test_items", "item_id", "itm-01")
        deleted_row = self.repo.read("test_items", "item_id", "itm-01")
        self.assertIsNone(deleted_row)

    def test_create_empty_fails(self):
        """Verifies that attempting to create empty records fails validation."""
        with self.assertRaises(RepositoryError):
            self.repo.create("test_items", {})


if __name__ == "__main__":
    unittest.main()
