"""
Unit tests for judge.py - Trading Logic Correctness

Focus areas:
- Decimal precision in financial calculations
- Risk management enforcement (2% max risk)
- SL/TP validation
- Degens Mode removal verification
"""

import pytest
from decimal import Decimal
from core.judge import TheJudge


@pytest.fixture
def judge():
    """Create a TheJudge instance for testing."""
    return TheJudge()


@pytest.mark.unit
class TestLotSizeCalculation:
    """Test lot size calculation with Decimal precision."""
    
    def test_calculate_safe_lot_normal_case(self, judge):
        """Normal case: calculate lot size for standard trade."""
        balance = Decimal("1000.00")
        entry_price = Decimal("1.1000")
        sl_price = Decimal("1.0950")  # 50 pips SL
        min_lot = Decimal("0.01")
        step_lot = Decimal("0.01")
        
        lot = judge._calculate_safe_lot(
            balance=balance,
            entry_price=entry_price,
            sl_price=sl_price,
            min_lot=min_lot,
            step_lot=step_lot
        )
        
        # Verify lot is Decimal type (not float)
        assert isinstance(lot, Decimal), "Lot size must be Decimal, not float!"
        
        # Verify lot is positive and reasonable
        assert lot > Decimal("0"), "Lot size must be positive"
        assert lot >= min_lot, "Lot size must be >= minimum lot"
        
        # Verify 2% risk enforcement
        # Risk = lot * (entry - sl) * 100 (assuming $100 per lot per point)
        price_diff = abs(entry_price - sl_price)
        risk_amount = lot * price_diff * Decimal("100")
        risk_percent = (risk_amount / balance) * Decimal("100")
        
        # Should be close to 2% (within small tolerance for rounding)
        assert risk_percent <= Decimal("2.1"), f"Risk {risk_percent}% exceeds 2% limit!"
    
    def test_calculate_safe_lot_small_account_no_degens_mode(self, judge):
        """Security: Small accounts (<$50) should NOT get 40% risk (Degens Mode removed)."""
        small_balance = Decimal("30.00")  # Below $50 threshold
        entry_price = Decimal("1.1000")
        sl_price = Decimal("1.0950")
        min_lot = Decimal("0.01")
        step_lot = Decimal("0.01")
        
        lot = judge._calculate_safe_lot(
            balance=small_balance,
            entry_price=entry_price,
            sl_price=sl_price,
            min_lot=min_lot,
            step_lot=step_lot
        )
        
        # Calculate actual risk
        price_diff = abs(entry_price - sl_price)
        risk_amount = lot * price_diff * Decimal("100")
        risk_percent = (risk_amount / small_balance) * Decimal("100")
        
        # CRITICAL: Even for small accounts, risk must be <= 5% (MAX_RISK_PERCENT)
        # Degens Mode (40% risk) must be GONE
        assert risk_percent <= Decimal("5.1"), \
            f"DEGENS MODE DETECTED! Risk {risk_percent}% exceeds 5% max! Should be <= 5%"
    
    def test_calculate_safe_lot_excessive_risk_returns_zero(self, judge):
        """Edge case: If even min lot exceeds max risk, return 0 (no trade)."""
        tiny_balance = Decimal("10.00")
        entry_price = Decimal("1.1000")
        sl_price = Decimal("1.0500")  # 500 pips SL (huge!)
        min_lot = Decimal("0.10")  # Minimum lot too large for this balance
        step_lot = Decimal("0.01")
        
        lot = judge._calculate_safe_lot(
            balance=tiny_balance,
            entry_price=entry_price,
            sl_price=sl_price,
            min_lot=min_lot,
            step_lot=step_lot
        )
        
        # Should return 0 (trade aborted due to excessive risk)
        assert lot == Decimal("0.0"), "Should abort trade if min lot exceeds max risk"
    
    def test_decimal_precision_no_float_errors(self, judge):
        """Verify Decimal arithmetic prevents float precision errors."""
        balance = Decimal("1000.00")
        entry_price = Decimal("1.10001")  # Odd precision
        sl_price = Decimal("1.09876")
        min_lot = Decimal("0.01")
        step_lot = Decimal("0.01")
        
        lot = judge._calculate_safe_lot(
            balance=balance,
            entry_price=entry_price,
            sl_price=sl_price,
            min_lot=min_lot,
            step_lot=step_lot
        )
        
        # Verify result is Decimal with proper precision (2 decimal places for lot)
        assert isinstance(lot, Decimal)
        assert lot == lot.quantize(Decimal("0.01")), \
            "Lot size must be rounded to 2 decimal places"


@pytest.mark.unit
class TestSLTPValidation:
    """Test Stop Loss / Take Profit validation logic."""
    
    def test_validate_sl_tp_buy_order_valid(self, judge):
        """Valid BUY order: SL below entry, TP above entry."""
        entry = Decimal("1.1000")
        sl = Decimal("1.0950")  # Below entry
        tp = Decimal("1.1100")  # Above entry
        
        is_valid = judge._validate_sl_tp(
            entry_price=entry,
            sl=sl,
            tp=tp,
            is_buy=True
        )
        
        assert is_valid is True
    
    def test_validate_sl_tp_buy_order_invalid_sl_above_entry(self, judge):
        """Invalid BUY: SL above entry (wrong direction)."""
        entry = Decimal("1.1000")
        sl = Decimal("1.1050")  # ABOVE entry (wrong!)
        tp = Decimal("1.1100")
        
        is_valid = judge._validate_sl_tp(
            entry_price=entry,
            sl=sl,
            tp=tp,
            is_buy=True
        )
        
        assert is_valid is False, "SL above entry for BUY should be invalid"
    
    def test_validate_sl_tp_sell_order_valid(self, judge):
        """Valid SELL order: SL above entry, TP below entry."""
        entry = Decimal("1.1000")
        sl = Decimal("1.1050")  # Above entry
        tp = Decimal("1.0900")  # Below entry
        
        is_valid = judge._validate_sl_tp(
            entry_price=entry,
            sl=sl,
            tp=tp,
            is_buy=False
        )
        
        assert is_valid is True
    
    def test_validate_sl_tp_minimum_distance(self, judge):
        """Invalid: SL too close to entry (< 10 pips)."""
        entry = Decimal("1.1000")
        sl = Decimal("1.0999")  # Only 1 pip away (too close!)
        tp = Decimal("1.1100")
        
        is_valid = judge._validate_sl_tp(
            entry_price=entry,
            sl=sl,
            tp=tp,
            is_buy=True
        )
        
        assert is_valid is False, "SL too close to entry should be invalid"


@pytest.mark.unit
class TestRiskManagementConstants:
    """Verify risk management constants are production-ready."""
    
    def test_risk_percent_is_2_percent(self, judge):
        """CRITICAL: Risk per trade must be 2%."""
        assert judge.RISK_PERCENT == Decimal("0.02"), \
            "RISK_PERCENT must be 2% (0.02)"
    
    def test_max_risk_percent_is_5_percent(self, judge):
        """CRITICAL: Maximum risk cap must be 5%."""
        assert judge.MAX_RISK_PERCENT == Decimal("0.05"), \
            "MAX_RISK_PERCENT must be 5% (0.05)"
