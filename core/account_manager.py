"""
Account Manager - Manage trading account information
Stores account details dari MT5 untuk proper lot calculation
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from decimal import Decimal, ROUND_DOWN
from threading import Lock
from dataclasses import dataclass, asdict
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AccountInfo:
    """Trading account information."""
    account_id: str
    account_type: str  # 'normal' atau 'micro'
    balance: float
    equity: float
    margin_free: float
    leverage: int
    currency: str
    min_lot: float
    max_lot: float
    lot_step: float
    is_micro: bool
    last_update: datetime
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AccountInfo':
        """Create AccountInfo from dictionary."""
        return cls(
            account_id=data.get('account_id', ''),
            account_type=data.get('account_type', 'normal'),
            balance=data.get('balance', 0.0),
            equity=data.get('equity', 0.0),
            margin_free=data.get('margin_free', 0.0),
            leverage=data.get('leverage', 100),
            currency=data.get('currency', 'USD'),
            min_lot=data.get('min_lot', 0.01),
            max_lot=data.get('max_lot', 100.0),
            lot_step=data.get('lot_step', 0.01),
            is_micro=data.get('is_micro', False),
            last_update=datetime.fromisoformat(data['last_update']) if 'last_update' in data else datetime.now()
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'account_id': self.account_id,
            'account_type': self.account_type,
            'balance': self.balance,
            'equity': self.equity,
            'margin_free': self.margin_free,
            'leverage': self.leverage,
            'currency': self.currency,
            'min_lot': self.min_lot,
            'max_lot': self.max_lot,
            'lot_step': self.lot_step,
            'is_micro': self.is_micro,
            'last_update': self.last_update.isoformat()
        }


class AccountManager:
    """
    Manages trading account information.
    
    Features:
    - Store account details dari MT5
    - Calculate proper lot sizes based on account type
    - Track account health (margin, equity)
    - Support multiple accounts
    """
    
    STORAGE_FILE = "config/account_info.json"
    MAX_AGE_SECONDS = 300  # Data valid untuk 5 menit
    
    def __init__(self):
        self.accounts: Dict[str, AccountInfo] = {}
        self._lock = Lock()
        self._load_accounts()
        logger.info("AccountManager initialized")
    
    def update_account(self, account_data: Dict) -> bool:
        """
        Update atau create account information.
        
        Expected data:
        {
            'account_id': '12345',
            'account_type': 'normal',  # atau 'micro'
            'balance': 10000.0,
            'equity': 9950.0,
            'margin_free': 9000.0,
            'leverage': 100,
            'currency': 'USD',
            'min_lot': 0.01,  # 0.01 untuk normal, 0.1 untuk micro
            'max_lot': 100.0,
            'lot_step': 0.01  # 0.01 untuk normal, 0.1 untuk micro
        }
        """
        try:
            with self._lock:
                account_id = account_data.get('account_id', 'default')
                
                # Detect micro account
                is_micro = self._detect_micro_account(account_data)
                account_data['is_micro'] = is_micro
                
                # Ensure correct lot sizes untuk micro
                if is_micro:
                    account_data['min_lot'] = max(account_data.get('min_lot', 0.1), 0.1)
                    account_data['lot_step'] = max(account_data.get('lot_step', 0.1), 0.1)
                
                account_data['last_update'] = datetime.now().isoformat()
                
                account = AccountInfo.from_dict(account_data)
                self.accounts[account_id] = account
                
                self._save_accounts()
                
                logger.info(
                    f"Account updated: {account_id} | "
                    f"Type: {account.account_type} | "
                    f"Balance: ${account.balance:.2f} | "
                    f"Min Lot: {account.min_lot}"
                )
                return True
        
        except Exception as e:
            logger.error(f"Failed to update account: {e}")
            return False
    
    def _detect_micro_account(self, data: Dict) -> bool:
        """Detect if account is micro based on lot sizes."""
        min_lot = data.get('min_lot', 0.01)
        account_type = data.get('account_type', '').lower()
        
        # Check by min lot size
        if min_lot >= 0.1:
            return True
        
        # Check by account type string
        if 'micro' in account_type or 'cent' in account_type:
            return True
        
        return False
    
    def get_account(self, account_id: str = 'default') -> Optional[AccountInfo]:
        """Get account information."""
        with self._lock:
            account = self.accounts.get(account_id)
            
            if account:
                # Check if data is stale
                age = (datetime.now() - account.last_update).total_seconds()
                if age > self.MAX_AGE_SECONDS:
                    logger.warning(f"Account {account_id} data is stale ({age:.0f}s old)")
            
            return account
    
    def get_default_account(self) -> Optional[AccountInfo]:
        """Get default account."""
        # Try 'default' first, then first available
        if 'default' in self.accounts:
            return self.accounts['default']
        
        # Return first account if any
        if self.accounts:
            return next(iter(self.accounts.values()))
        
        return None
    
    def calculate_lot_size(self, risk_amount: float, stop_loss_pips: float, 
                          pip_value: float, symbol: str = '', 
                          account_id: str = 'default') -> float:
        """
        Calculate proper lot size based on risk parameters dan account type.
        
        Args:
            risk_amount: Amount to risk in account currency
            stop_loss_pips: Stop loss dalam pips
            pip_value: Value of 1 pip per lot
            symbol: Trading symbol
            account_id: Account identifier
        
        Returns:
            Proper lot size adjusted untuk account type
        """
        account = self.get_account(account_id)
        
        if not account:
            logger.warning("No account info, using default lot calculation")
            # Default calculation
            if stop_loss_pips > 0 and pip_value > 0:
                lot = risk_amount / (stop_loss_pips * pip_value)
                return round(lot, 2)
            return 0.01
        
        # Calculate lot size
        if stop_loss_pips <= 0 or pip_value <= 0:
            logger.error("Invalid SL atau pip value")
            return account.min_lot
        
        # Base calculation
        lot_size = risk_amount / (stop_loss_pips * pip_value)
        
        # Adjust untuk account constraints
        # Round to lot step
        lot_step = account.lot_step
        lot_size = round(lot_size / lot_step) * lot_step
        
        # Clamp to min/max
        lot_size = max(account.min_lot, min(account.max_lot, lot_size))
        
        # Round to proper decimals
        decimals = len(str(lot_step).split('.')[-1]) if '.' in str(lot_step) else 0
        lot_size = round(lot_size, decimals)
        
        logger.debug(
            f"Lot calculation: Risk=${risk_amount:.2f}, SL={stop_loss_pips}pips, "
            f"PipValue=${pip_value:.5f} → Lot={lot_size} ({account.account_type})"
        )
        
        return lot_size
    
    def validate_lot_size(self, lot_size: float, account_id: str = 'default') -> tuple[bool, float]:
        """
        Validate dan adjust lot size untuk account constraints.
        
        Returns:
            (is_valid, adjusted_lot_size)
        """
        account = self.get_account(account_id)
        
        if not account:
            # Default validation (assume normal account)
            adjusted = max(0.01, min(100.0, lot_size))
            adjusted = round(adjusted, 2)
            return adjusted == lot_size, adjusted
        
        # Check minimum
        if lot_size < account.min_lot:
            logger.warning(f"Lot size {lot_size} below minimum {account.min_lot}")
            return False, account.min_lot
        
        # Check maximum
        if lot_size > account.max_lot:
            logger.warning(f"Lot size {lot_size} above maximum {account.max_lot}")
            return False, account.max_lot
        
        # Check step size
        lot_step = account.lot_step
        remainder = lot_size % lot_step
        if remainder > 0.0001:  # Small tolerance
            adjusted = round(lot_size / lot_step) * lot_step
            logger.warning(f"Lot size {lot_size} not aligned with step {lot_step}, adjusted to {adjusted}")
            return False, adjusted
        
        return True, lot_size
    
    def get_risk_settings(self, account_id: str = 'default', mode: str = 'safe') -> Dict:
        """
        Get risk settings based on account balance dan mode.
        
        Returns proper risk percentages untuk positive expectancy.
        """
        account = self.get_account(account_id)
        
        if not account:
            # Default conservative settings
            return {
                'risk_per_trade': 0.02,
                'max_daily_risk': 0.04,
                'min_rrr': 2.0,  # Risk-Reward Ratio
                'target_winrate': 0.45,  # Focus on RRR, not winrate
                'max_consecutive_losses': 3,
                'account_type': 'normal',
                'min_lot': 0.01,
                'is_micro': False
            }
        
        # Mode-based settings
        # Fokus: Positive Expectancy = (WinRate × AvgWin) - (LossRate × AvgLoss)
        # Target: RRR 1:2+ dengan winrate 40-50%
        
        mode_settings = {
            'safe': {
                'risk_per_trade': 0.01,  # 1% per trade
                'max_daily_risk': 0.03,  # 3% max daily
                'min_rrr': 2.5,  # Minimum 1:2.5 RRR
                'target_winrate': 0.45,  # 45% winrate acceptable dengan RRR 2.5
                'max_consecutive_losses': 5,
            },
            'balanced': {
                'risk_per_trade': 0.02,  # 2% per trade
                'max_daily_risk': 0.04,  # 4% max daily
                'min_rrr': 2.0,  # Minimum 1:2 RRR
                'target_winrate': 0.40,  # 40% winrate acceptable dengan RRR 2.0
                'max_consecutive_losses': 4,
            },
            'aggressive': {
                'risk_per_trade': 0.03,  # 3% per trade
                'max_daily_risk': 0.06,  # 6% max daily
                'min_rrr': 1.5,  # Minimum 1:1.5 RRR
                'target_winrate': 0.50,  # 50% winrate target
                'max_consecutive_losses': 3,
            },
            'sniper': {
                'risk_per_trade': 0.015,  # 1.5% per trade (quality over quantity)
                'max_daily_risk': 0.03,   # 3% max daily
                'min_rrr': 3.0,  # Minimum 1:3 RRR (high quality setups only)
                'target_winrate': 0.35,   # 35% winrate acceptable dengan RRR 3.0
                'max_consecutive_losses': 4,
                'min_confidence': 0.75,   # High confidence only
            }
        }
        
        settings = mode_settings.get(mode, mode_settings['balanced']).copy()
        
        # Add account info
        settings.update({
            'account_type': account.account_type,
            'account_balance': account.balance,
            'account_equity': account.equity,
            'min_lot': account.min_lot,
            'max_lot': account.max_lot,
            'lot_step': account.lot_step,
            'is_micro': account.is_micro,
            'leverage': account.leverage
        })
        
        # Calculate actual risk amounts
        settings['risk_amount_per_trade'] = account.balance * settings['risk_per_trade']
        settings['max_daily_loss'] = account.balance * settings['max_daily_risk']
        
        return settings
    
    def can_trade(self, account_id: str = 'default') -> tuple[bool, str]:
        """Check if account is in good condition untuk trading."""
        account = self.get_account(account_id)
        
        if not account:
            return False, "No account information"
        
        # Check data freshness
        age = (datetime.now() - account.last_update).total_seconds()
        if age > self.MAX_AGE_SECONDS:
            return False, f"Account data stale ({age:.0f}s old)"
        
        # Check balance
        if account.balance < 100:
            return False, f"Insufficient balance: ${account.balance:.2f}"
        
        # Check margin
        if account.margin_free < account.balance * 0.5:
            return False, f"Low free margin: ${account.margin_free:.2f}"
        
        return True, "Account OK"
    
    def get_account_summary(self) -> Dict:
        """Get summary of all accounts."""
        with self._lock:
            summary = {
                'total_accounts': len(self.accounts),
                'accounts': {}
            }
            
            for account_id, account in self.accounts.items():
                age = (datetime.now() - account.last_update).total_seconds()
                summary['accounts'][account_id] = {
                    'type': account.account_type,
                    'balance': account.balance,
                    'equity': account.equity,
                    'is_micro': account.is_micro,
                    'min_lot': account.min_lot,
                    'data_age_seconds': int(age)
                }
            
            return summary
    
    def _save_accounts(self):
        """Save accounts to file."""
        try:
            os.makedirs(os.path.dirname(self.STORAGE_FILE), exist_ok=True)
            
            data = {
                'saved_at': datetime.now().isoformat(),
                'accounts': {k: v.to_dict() for k, v in self.accounts.items()}
            }
            
            with open(self.STORAGE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        
        except Exception as e:
            logger.error(f"Failed to save accounts: {e}")
    
    def _load_accounts(self):
        """Load accounts from file."""
        try:
            if os.path.exists(self.STORAGE_FILE):
                with open(self.STORAGE_FILE, 'r') as f:
                    data = json.load(f)
                
                for account_id, account_data in data.get('accounts', {}).items():
                    self.accounts[account_id] = AccountInfo.from_dict(account_data)
                
                logger.info(f"Loaded {len(self.accounts)} accounts")
        
        except Exception as e:
            logger.error(f"Failed to load accounts: {e}")
            self.accounts = {}
    
    def clear_account(self, account_id: str):
        """Remove account."""
        with self._lock:
            if account_id in self.accounts:
                del self.accounts[account_id]
                self._save_accounts()
                logger.info(f"Cleared account {account_id}")


# Singleton
_account_manager = None

def get_account_manager() -> AccountManager:
    """Get global AccountManager instance."""
    global _account_manager
    if _account_manager is None:
        _account_manager = AccountManager()
    return _account_manager
