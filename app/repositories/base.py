from typing import Any, Dict, List, Optional
from app.database.connection import DatabaseManager, db_manager
from app.core.exceptions import DatabaseError, RepositoryError
from app.core.logging import logger


class BaseRepository:
    """Generic data access class providing CRUD operations and SQL query helper functions."""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or db_manager

    def _filter_fields_by_schema(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prunes dictionary keys that do not correspond to column names in the destination SQLite table."""
        try:
            columns_info = self.db.execute_read(f"PRAGMA table_info({table});")
            valid_columns = {col["name"] for col in columns_info}
            return {k: v for k, v in data.items() if k in valid_columns}
        except Exception as e:
            logger.warning(f"Failed to query table info for column filtering on table {table}: {str(e)}")
            return data

    def create(self, table: str, data: Dict[str, Any]) -> Any:
        """Inserts a record dictionary into the specified table using parameterized queries, dynamically pruning invalid keys."""
        if not data:
            raise RepositoryError("Cannot insert empty record.")
            
        filtered_data = self._filter_fields_by_schema(table, data)
        if not filtered_data:
            raise RepositoryError(f"Cannot insert empty record after schema pruning in {table}.")

        columns = ", ".join(filtered_data.keys())
        placeholders = ", ".join("?" for _ in filtered_data)
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders});"
        params = tuple(filtered_data.values())
        
        try:
            logger.debug(f"Inserting into {table}: {list(filtered_data.keys())}")
            return self.db.execute_write(query, params)
        except DatabaseError as e:
            logger.error(f"Failed to create record in {table}: {str(e)}")
            raise RepositoryError(f"Failed to create record in {table}", details=str(e))

    def read(self, table: str, id_column: str, id_value: Any) -> Optional[Dict[str, Any]]:
        """Retrieves a single record from the table matching id_column = id_value."""
        query = f"SELECT * FROM {table} WHERE {id_column} = ?;"
        
        try:
            logger.debug(f"Reading from {table} where {id_column} = {id_value}")
            return self.db.execute_read_one(query, (id_value,))
        except DatabaseError as e:
            logger.error(f"Failed to read record from {table}: {str(e)}")
            raise RepositoryError(f"Failed to read record from {table}", details=str(e))

    def update(self, table: str, id_column: str, id_value: Any, data: Dict[str, Any]) -> int:
        """Updates fields of a record matching id_column = id_value with database schema-validated dictionary values."""
        if not data:
            return 0
            
        filtered_data = self._filter_fields_by_schema(table, data)
        if not filtered_data:
            return 0

        sets = ", ".join(f"{key} = ?" for key in filtered_data.keys())
        query = f"UPDATE {table} SET {sets} WHERE {id_column} = ?;"
        params = tuple(filtered_data.values()) + (id_value,)
        
        try:
            logger.debug(f"Updating {table} where {id_column} = {id_value}")
            return self.db.execute_write(query, params)
        except DatabaseError as e:
            logger.error(f"Failed to update record in {table}: {str(e)}")
            raise RepositoryError(f"Failed to update record in {table}", details=str(e))

    def delete(self, table: str, id_column: str, id_value: Any) -> int:
        """Deletes a record matching id_column = id_value from the table."""
        query = f"DELETE FROM {table} WHERE {id_column} = ?;"
        
        try:
            logger.debug(f"Deleting from {table} where {id_column} = {id_value}")
            return self.db.execute_write(query, (id_value,))
        except DatabaseError as e:
            logger.error(f"Failed to delete record from {table}: {str(e)}")
            raise RepositoryError(f"Failed to delete record from {table}", details=str(e))

    def list_all(self, table: str) -> List[Dict[str, Any]]:
        """Lists all records from the specified table."""
        query = f"SELECT * FROM {table};"
        
        try:
            logger.debug(f"Listing all records from {table}")
            return self.db.execute_read(query)
        except DatabaseError as e:
            logger.error(f"Failed to list records from {table}: {str(e)}")
            raise RepositoryError(f"Failed to list records from {table}", details=str(e))
