"""
Database migration runner.

Applies SQL migration files to the database.
"""

import sqlite3
import os
import hashlib
from pathlib import Path
from typing import List
from core.logger import get_logger

logger = get_logger(__name__)

class MigrationRunner:
    """Handles database schema migrations."""
    
    def __init__(self, db_path: str, migrations_dir: str = "migrations"):
        """
        Initialize migration runner.
        
        Args:
            db_path: Path to SQLite database
            migrations_dir: Directory containing .sql migration files
        """
        self.db_path = db_path
        self.migrations_dir = Path(migrations_dir)
        self._init_migrations_table()
    
    def _init_migrations_table(self):
        """Create migrations tracking table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_name TEXT UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of already applied migrations."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT migration_name FROM schema_migrations ORDER BY id")
        applied = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return applied
    
    def get_pending_migrations(self) -> List[Path]:
        """Get list of migration files that haven't been applied yet."""
        if not self.migrations_dir.exists():
            return []
        
        applied = set(self.get_applied_migrations())
        
        # Find all .sql files
        all_migrations = sorted(self.migrations_dir.glob("*.sql"))
        
        # Filter out already applied
        pending = [
            m for m in all_migrations 
            if m.name not in applied
        ]
        
        return pending
    
    def apply_migration(self, migration_path: Path):
        """
        Apply a single migration file.
        
        Args:
            migration_path: Path to .sql file
        """
        logger.info(f"Applying migration: {migration_path.name}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Read SQL file
            with open(migration_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            # Calculate checksum for verification
            checksum = hashlib.md5(sql_script.encode('utf-8')).hexdigest()

            # Execute migration
            cursor.executescript(sql_script)
            
            # Record migration as applied
            cursor.execute(
                "INSERT INTO schema_migrations (migration_name) VALUES (?)",
                (migration_path.name,)
            )
            
            conn.commit()
            logger.info(f"Migration applied successfully: {migration_path.name}", extra={"context": {"checksum": checksum}})
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Migration failed: {migration_path.name} - {e}", extra={"context": {"error": str(e)}})
            raise
        
        finally:
            conn.close()
    
    def run_pending_migrations(self):
        """Apply all pending migrations in order."""
        pending = self.get_pending_migrations()
        
        if not pending:
            logger.info("No pending migrations found")
            return
        
        logger.info(f"Found {len(pending)} pending migration(s)")
        
        for migration_path in pending:
            self.apply_migration(migration_path)
        
        logger.info("All migrations applied successfully!")


from core.appdata import get_appdata_path

def run_migrations(db_path: str = None):
    """
    Convenience function to run all pending migrations.
    
    Args:
        db_path: Path to database file. If None, uses default AppData location.
    """
    if db_path is None:
        db_path = get_appdata_path("database/trade_history.db")
        
    runner = MigrationRunner(db_path)
    runner.run_pending_migrations()


if __name__ == "__main__":
    # Run migrations when executed directly
    run_migrations()
