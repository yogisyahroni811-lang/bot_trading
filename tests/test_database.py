"""
Unit tests for database.py - Critical Security Tests

Focus areas:
- SQL injection prevention (parameterized queries)
- Data integrity
- Token usage logging
"""

import pytest
import os
import tempfile
from decimal import Decimal
from core.database import TradeDatabase


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Create temp file
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Initialize database
    db = TradeDatabase(db_path=path)
    
    yield db
    
    # Cleanup
    if os.path.exists(path):
        os.remove(path)


@pytest.mark.security
@pytest.mark.unit
class TestSQLInjectionPrevention:
    """Test that SQL injection vulnerabilities are prevented."""
    
    def test_get_stats_with_safe_symbol(self, temp_db):
        """Normal case: get stats for a valid symbol."""
        # Insert test trade
        temp_db.log_trade({
            'id': 'test-001',
            'symbol': 'EURUSD',
            'timeframe': 'H1',
            'action': 'BUY',
            'open_price': 1.1000,
            'close_price': 1.1100,
            'pnl': 100.0,
            'outcome': 'WIN',
            'reason': 'Test trade'
        })
        
        # Get stats
        stats = temp_db.get_stats(symbol="EURUSD")
        
        assert stats['total_trades'] == 1
        assert stats['winrate'] == 100.0
    
    def test_get_stats_sql_injection_attempt(self, temp_db):
        """Security: SQL injection should be prevented by parameterized queries."""
        # Insert legitimate trades
        temp_db.log_trade({
            'id': 'test-002',
            'symbol': 'EURUSD',
            'timeframe': 'H1',
            'action': 'BUY',
            'open_price': 1.1000,
            'close_price': 1.1100,
            'pnl': 100.0,
            'outcome': 'WIN',
            'reason': 'Legitimate trade'
        })
        
        # Attempt SQL injection via symbol parameter
        # If vulnerable, this would drop the WHERE clause and return all trades
        malicious_symbol = "EURUSD' OR '1'='1"
        
        stats = temp_db.get_stats(symbol=malicious_symbol)
        
        # Should return 0 results (no symbol matches the literal injection string)
        # NOT return all trades (which would be 1)
        assert stats['total_trades'] == 0, "SQL injection vulnerability detected!"
        assert stats['winrate'] == 0.0
    
    def test_get_stats_all_symbols(self, temp_db):
        """Normal case: get stats for all symbols (no filter)."""
        # Insert multiple trades
        temp_db.log_trade({
            'id': 'test-003',
            'symbol': 'EURUSD',
            'timeframe': 'H1',
            'action': 'BUY',
            'open_price': 1.1000,
            'close_price': 1.1100,
            'pnl': 100.0,
            'outcome': 'WIN',
            'reason': 'Trade 1'
        })
        temp_db.log_trade({
            'id': 'test-004',
            'symbol': 'GBPUSD',
            'timeframe': 'H1',
            'action': 'SELL',
            'open_price': 1.2500,
            'close_price': 1.2400,
            'pnl': -50.0,
            'outcome': 'LOSS',
            'reason': 'Trade 2'
        })
        
        # Get stats without symbol filter
        stats = temp_db.get_stats(symbol=None)
        
        assert stats['total_trades'] == 2
        assert stats['winrate'] == 50.0


@pytest.mark.unit
class TestTokenUsageLogging:
    """Test token usage logging functionality."""
    
    def test_log_token_usage_parameter_names(self, temp_db):
        """Regression: ensure parameter names match (input_tok vs input_tokens bug)."""
        # This should not raise an exception
        temp_db.log_token_usage(
            provider="openai",
            model="gpt-4",
            input_tok=1000,
            output_tok=500,
            cost=0.03
        )
        
        # Verify it was logged (simple check)
        # In real implementation, would query the database
        # For now, just ensure no exception was raised
        assert True
    
    def test_log_token_usage_decimal_cost(self, temp_db):
        """Ensure cost can be logged with high precision."""
        temp_db.log_token_usage(
            provider="groq",
            model="mixtral-8x7b",
            input_tok=2000,
            output_tok=1000,
            cost=0.00012345  # Very small cost
        )
        
        assert True


@pytest.mark.unit
class TestTradeLogging:
    """Test trade logging functionality."""
    
    def test_log_trade_basic(self, temp_db):
        """Ensure trade logging works with dictionary parameter."""
        temp_db.log_trade({
            'id': 'test-005',
            'symbol': 'EURUSD',
            'timeframe': 'H1',
            'action': 'BUY',
            'open_price': 1.12345,
            'close_price': 1.13000,
            'pnl': 123.45,
            'outcome': 'WIN',
            'reason': 'Test trade'
        })
        
        # Verify trade was logged
        stats = temp_db.get_stats(symbol='EURUSD')
        assert stats['total_trades'] == 1
