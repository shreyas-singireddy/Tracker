import re
from pathlib import Path
from typing import Optional
from app.database.connection import DatabaseManager, db_manager
from app.core.exceptions import DatabaseError
from app.core.logging import logger

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


class MigrationRunner:
    """Discovers, tracks, and applies versioned SQL database migrations safely inside transactions."""

    def __init__(self, migrations_dir: Path = MIGRATIONS_DIR, db: Optional[DatabaseManager] = None):
        self.migrations_dir = migrations_dir
        self.db = db or db_manager
        logger.debug(f"MigrationRunner initialized with migrations directory: {self.migrations_dir}")

    def init_migration_table(self):
        """Ensures the schema_migrations tracking table exists in the database."""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            self.db.execute_write(create_table_query)
            logger.debug("schema_migrations table verified/created.")
        except DatabaseError as e:
            logger.error(f"Failed to initialize migration table: {str(e)}")
            raise

    def get_applied_migrations(self) -> set:
        """Retrieves a set of all previously applied migration versions."""
        query = "SELECT version FROM schema_migrations;"
        try:
            rows = self.db.execute_read(query)
            return {row["version"] for row in rows}
        except DatabaseError as e:
            logger.error(f"Failed to fetch applied migrations: {str(e)}")
            raise

    def get_migration_files(self) -> list:
        """Finds and returns sorted list of all SQL migration files."""
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory does not exist: {self.migrations_dir}")
            return []
            
        sql_files = list(self.migrations_dir.glob("*.sql"))
        # Sort files numerically/alphabetically by filename
        sql_files.sort(key=lambda p: p.name)
        return sql_files

    def apply_migration(self, filepath: Path):
        """Reads and executes a single SQL migration file inside a transaction."""
        filename = filepath.name
        logger.info(f"Applying migration: {filename}")
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                sql_content = f.read()

            # Split statements by semicolon if needed, or execute as a script.
            # sqlite3 execute() handles a single query. executescript() executes multiple SQL statements.
            # We'll use our transaction helper and execute SQL as a script.
            with self.db.transaction() as conn:
                cursor = conn.cursor()
                # Run the migration SQL script
                cursor.executescript(sql_content)
                # Register applied migration in schema_migrations table
                cursor.execute(
                    "INSERT INTO schema_migrations (version) VALUES (?);", 
                    (filename,)
                )
                cursor.close()
                
            logger.info(f"Successfully applied migration: {filename}")
        except Exception as e:
            logger.error(f"Failed to apply migration {filename}: {str(e)}")
            raise DatabaseError(f"Migration {filename} failed and was rolled back.", details=str(e))

    def run_all(self):
        """Executes the complete migration sequence, applying any outstanding updates."""
        logger.info("Starting database migration runner...")
        self.init_migration_table()
        
        applied = self.get_applied_migrations()
        files = self.get_migration_files()
        
        applied_count = 0
        for filepath in files:
            filename = filepath.name
            if filename not in applied:
                self.apply_migration(filepath)
                applied_count += 1
            else:
                logger.debug(f"Migration {filename} already applied. Skipping.")
                
        if applied_count > 0:
            logger.info(f"Database migration completed. Applied {applied_count} migrations.")
        else:
            logger.info("Database is up to date. No migrations to apply.")


# Global runner instance
migration_runner = MigrationRunner()

