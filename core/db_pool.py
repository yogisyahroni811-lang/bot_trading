"""
Database connection pooling and optimized query execution.

Implements thread-safe connection pool for SQLite to avoid overhead of
creating new connections for every operation.
"""

import sqlite3
import threading
from queue import Queue, Empty
from typing import Optional
from contextlib import contextmanager


class ConnectionPool:
    """Thread-safe SQLite connection pool."""
    
    def __init__(self, db_path: str, pool_size: int = 3):
        """
        Initialize connection pool.
        
        Args:
            db_path: Path to SQLite database file
            pool_size: Max number of connections in pool (default: 3)
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self._pool: Queue = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._created_connections = 0
        
        # Pre-create connections
        for _ in range(pool_size):
            self._pool.put(self._create_connection())
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with optimizations."""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,  # Allow connection sharing across threads
            timeout=10.0  # 10s timeout for locked DB
        )
        
        # Performance optimizations
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for concurrency
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety vs speed
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        conn.execute("PRAGMA temp_store=MEMORY")  # Store temp tables in memory
        
        self._created_connections += 1
        return conn
    
    @contextmanager
    def get_connection(self):
        """
        Get connection from pool (context manager).
        
        Usage:
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(...)
        """
        conn = None
        try:
            # Try to get connection from pool
            try:
                conn = self._pool.get(block=True, timeout=5.0)
            except Empty:
                # Pool exhausted, create new connection (up to limit)
                with self._lock:
                    if self._created_connections < self.pool_size * 2:  # Max 2x pool size
                        conn = self._create_connection()
                    else:
                        # Fallback: wait longer for available connection
                        conn = self._pool.get(block=True, timeout=30.0)
            
            yield conn
            
        finally:
            if conn:
                # Return connection to pool
                try:
                    self._pool.put_nowait(conn)
                except:
                    # Pool full, close connection
                    conn.close()
    
    def close_all(self):
        """Close all connections in pool."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Empty:
                break


# Global pool instance
_pool: Optional[ConnectionPool] = None
_pool_lock = threading.Lock()


def get_pool(db_path: str = "trade_history.db") -> ConnectionPool:
    """
    Get global connection pool instance (singleton).
    
    Args:
        db_path: Database file path
        
    Returns:
        ConnectionPool instance
    """
    global _pool
    
    if _pool is None:
        with _pool_lock:
            if _pool is None:  # Double-check locking
                _pool = ConnectionPool(db_path, pool_size=3)
    
    return _pool
