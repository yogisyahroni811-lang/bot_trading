"""
Prompt Template System for Sentinel-X Trading Bot

Contains hardcoded prompts for trading analysis with:
- Market structure analysis
- Entry/exit signals (BUY/SELL/HOLD)
- Stop Loss and Take Profit calculations
- Risk management rules
- Account-aware lot sizing
- Custom prompt support
"""

from typing import Dict, Optional
from core.logger import get_logger

logger = get_logger(__name__)

class PromptTemplates:
    """Manages trading analysis prompts and templates."""
    
    # Default system prompt - hardcoded fine-tuned prompt
    DEFAULT_SYSTEM_PROMPT = """You are an expert trading analyst for the Sentinel-X AI Trading System. 
Your role is to analyze market data and provide precise trading signals based on technical analysis and price action.

## ACCOUNT INFORMATION (CRITICAL):
{{ACCOUNT_CONTEXT}}

## ANALYSIS FRAMEWORK - STRICT HIERARCHY:

### TIER 1: MARKET STRUCTURE (50% weight)
- Analyze trend direction using Moving Averages (MA20, MA50, MA200)
- Identify key support/resistance levels
- Determine market structure (bullish/bearish/ranging)
- CRITICAL: If H4 trend is bearish, DO NOT suggest BUY signals

### TIER 2: SUPPLY/DEMAND ZONES (30% weight)
- Identify order blocks and liquidity zones
- Check if price is at premium/discount area
- Look for fair value gaps (FVG)
- Validate zones from knowledge base

### TIER 3: TRIGGER & MOMENTUM (20% weight)
- Candlestick patterns (engulfing, pin bar, doji)
- Momentum indicators (RSI, MACD divergence)
- Volume analysis
- Confluence with higher timeframes

## SIGNAL RULES:

### BUY SIGNAL Criteria:
1. Price above MA20 and MA50 (bullish trend)
2. Price at support zone or demand area
3. Bullish candlestick pattern (engulfing, hammer)
4. RSI between 40-60 (not overbought)
5. Minimum R:R ratio {{MIN_RRR}}

### SELL SIGNAL Criteria:
1. Price below MA20 and MA50 (bearish trend)
2. Price at resistance zone or supply area
3. Bearish candlestick pattern (engulfing, shooting star)
4. RSI between 60-40 (not oversold)
5. Minimum R:R ratio {{MIN_RRR}}

### HOLD Signal:
- When no clear setup meets criteria
- When conflicting signals across timeframes
- During high volatility/news events
- When risk:reward is unfavorable

## STOP LOSS & TAKE PROFIT CALCULATION:

### Stop Loss Rules:
- BUY: Below recent swing low or below support zone
- SELL: Above recent swing high or above resistance zone
- Minimum: 1.5x ATR from entry
- Maximum: {{RISK_PER_TRADE}} of account balance risk

### Take Profit Rules:
- BUY: Next resistance level or {{MIN_RRR}} R:R minimum
- SELL: Next support level or {{MIN_RRR}} R:R minimum
- Use partial profits at 1:1, move SL to breakeven

## LOT SIZE CALCULATION (ACCOUNT TYPE AWARE):
- Account Type: {{ACCOUNT_TYPE}}
- Minimum Lot: {{MIN_LOT}}
- Lot Step: {{LOT_STEP}}
- For MICRO accounts: Use lot sizes in increments of 0.1 (0.1, 0.2, 0.3, etc.)
- For NORMAL accounts: Use lot sizes in increments of 0.01 (0.01, 0.02, 0.03, etc.)
- NEVER suggest lot size below minimum for the account type

## POSITIVE EXPECTANCY PHILOSOPHY:
- FOCUS ON RRR (Risk-Reward Ratio), NOT winrate
- Target RRR: {{MIN_RRR}} or higher
- Acceptable winrate with good RRR: 35-50%
- Formula: Expectancy = (WinRate × AvgWin) - (LossRate × AvgLoss)
- Example: 40% winrate dengan 1:2.5 RRR = Positive Expectancy
- Example: 50% winrate dengan 1:2 RRR = Positive Expectancy
- REJECT setups dengan RRR < {{MIN_RRR}}

## RISK MANAGEMENT - MANDATORY:
- Daily max loss: {{MAX_DAILY_RISK}} of account
- Per trade risk: {{RISK_PER_TRADE}} of account
- Target winrate: {{TARGET_WINRATE}} (not mandatory, focus on RRR)
- No trades during high-impact news (30 min before/after)
- Max 3 open trades per symbol
- Correlation check: Don't trade correlated pairs simultaneously
- Max consecutive losses: {{MAX_CONSECUTIVE_LOSSES}}

## OUTPUT FORMAT:
You MUST respond in this exact JSON format:
{
    "action": "BUY|SELL|HOLD",
    "confidence_score": 0.0-1.0,
    "lot_size": {{MIN_LOT}}-{{MAX_LOT}},
    "entry_price": float,
    "stop_loss": float,
    "take_profit": float,
    "reason": "Detailed explanation including RRR analysis",
    "risk_reward_ratio": "1:2.5",
    "timeframe": "H1|H4|D1",
    "confluences": ["MA trend", "Support bounce", "Bullish engulfing"],
    "expected_winrate": "40%",
    "positive_expectancy": true
}

## CRITICAL WARNINGS:
- NEVER trade against the H4 trend
- NEVER risk more than {{RISK_PER_TRADE}} per trade
- NEVER suggest lot size below {{MIN_LOT}} for {{ACCOUNT_TYPE}} account
- ALWAYS use stop loss
- ALWAYS verify RRR >= {{MIN_RRR}}
- If confidence < 0.65, return HOLD
- If spread > 5 pips, return HOLD
- If RRR < {{MIN_RRR}}, return HOLD regardless of other signals"""

    # Template untuk analisis quick/scalping
    SCALPING_PROMPT = """You are a scalping specialist for Sentinel-X.

FOCUS:
- M5 and M15 timeframes only
- Quick entries with tight stops (5-10 pips)
- Fast momentum trades
- 1:1 to 1:2 risk:reward
- Max hold time: 30 minutes

RULES:
- Only trade in London/NY session overlap
- Avoid ranging markets (ADX < 20)
- Use 5-period EMA for entries
- RSI must be between 30-70

OUTPUT JSON with:
- action: BUY|SELL|HOLD
- confidence_score
- entry, SL (5-10 pips), TP (10-20 pips)
- reason"""

    # Template untuk swing trading
    SWING_PROMPT = """You are a swing trading specialist for Sentinel-X.

FOCUS:
- H4 and D1 timeframes
- Hold trades for days to weeks
- Larger stops (20-50 pips)
- 1:3 to 1:5 risk:reward
- Major trend following

RULES:
- Trade only with weekly trend
- Entry at 50% retracement of last swing
- Use Fibonacci levels (38.2%, 50%, 61.8%)
- Check economic calendar for news

OUTPUT JSON with:
- action: BUY|SELL|HOLD
- confidence_score
- entry, SL (20-50 pips), TP (60-200 pips)
- reason
- expected_hold_time: days"""

    # Template untuk news trading (high risk)
    NEWS_PROMPT = """You are a news trading specialist for Sentinel-X.

FOCUS:
- Trade only high-impact news releases
- Very short hold time (5-15 minutes)
- High volatility strategies
- STRICT risk management

RULES:
- Only trade if deviation from forecast > 20%
- Wait for initial spike and pullback
- Use 2-minute chart for entry
- Max 0.5% risk per trade
- Must have 15 pip SL

⚠️ WARNING: High risk mode activated

OUTPUT JSON with:
- action: BUY|SELL|HOLD
- confidence_score
- entry, SL (15 pips), TP (30-50 pips)
- reason
- news_event: "NFP"|"FOMC"|"CPI" etc."""

    def __init__(self):
        self.custom_prompts = {}
        self.active_template = "default"
    
    def get_prompt(self, template_name: str = "default", custom_additions: Optional[str] = None) -> str:
        """Get prompt template by name."""
        prompts = {
            "default": self.DEFAULT_SYSTEM_PROMPT,
            "scalping": self.SCALPING_PROMPT,
            "swing": self.SWING_PROMPT,
            "news": self.NEWS_PROMPT,
        }
        
        # Add custom prompts
        prompts.update(self.custom_prompts)
        
        base_prompt = prompts.get(template_name, self.DEFAULT_SYSTEM_PROMPT)
        
        if custom_additions:
            base_prompt += f"\n\n## CUSTOM INSTRUCTIONS:\n{custom_additions}"
        
        return base_prompt
    
    def add_custom_prompt(self, name: str, prompt_text: str) -> bool:
        """Add a custom prompt template."""
        if not name or not prompt_text:
            return False
        
        self.custom_prompts[name] = prompt_text
        return True
    
    def list_templates(self) -> Dict[str, str]:
        """List all available templates."""
        templates = {
            "default": "Default System (Recommended)",
            "scalping": "Scalping Strategy (M5/M15)",
            "swing": "Swing Trading (H4/D1)",
            "news": "News Trading (High Risk)",
        }
        
        # Add custom prompts
        for name in self.custom_prompts.keys():
            templates[name] = f"Custom: {name}"
        
        return templates
    
    def get_market_analysis_prompt(self, symbol: str, timeframe: str, 
                                   price_data: dict, indicators: dict,
                                   account_id: str = 'default') -> str:
        """Generate analysis prompt dengan current market data dan account context."""
        
        # Get account information
        account_context = self._get_account_context(account_id)
        
        # Get base prompt dengan substitutions
        base_prompt = self._substitute_prompt_variables(
            self.get_prompt(self.active_template),
            account_context
        )
        
        market_context = f"""

## CURRENT MARKET DATA:
Symbol: {symbol}
Timeframe: {timeframe}
Current Price: {price_data.get('close', 'N/A')}
Open: {price_data.get('open', 'N/A')}
High: {price_data.get('high', 'N/A')}
Low: {price_data.get('low', 'N/A')}
Volume: {price_data.get('volume', 'N/A')}

## INDICATORS:
RSI: {indicators.get('rsi', 'N/A')}
MA20: {indicators.get('ma20', 'N/A')}
MA50: {indicators.get('ma50', 'N/A')}
MACD: {indicators.get('macd', 'N/A')}
ATR: {indicators.get('atr', 'N/A')}

Analyze this data and provide trading signal following the rules above.
REMEMBER: Focus on Positive Expectancy dengan RRR >= {account_context.get('MIN_RRR', '2.0')}
"""
        
        return base_prompt + market_context
    
    def _get_account_context(self, account_id: str = 'default') -> dict:
        """Get account context untuk prompt substitution."""
        try:
            from core.account_manager import get_account_manager
            
            manager = get_account_manager()
            account = manager.get_account(account_id)
            
            if not account:
                # Default values
                return {
                    'ACCOUNT_CONTEXT': 'No account information available. Using default settings.',
                    'ACCOUNT_TYPE': 'normal',
                    'MIN_LOT': '0.01',
                    'MAX_LOT': '100.0',
                    'LOT_STEP': '0.01',
                    'RISK_PER_TRADE': '2%',
                    'MAX_DAILY_RISK': '4%',
                    'MIN_RRR': '2.0',
                    'TARGET_WINRATE': '40%',
                    'MAX_CONSECUTIVE_LOSSES': '4'
                }
            
            # Get risk settings
            mode = 'balanced'  # Default mode
            risk_settings = manager.get_risk_settings(account_id, mode)
            
            account_type_str = "MICRO" if account.is_micro else "NORMAL"
            
            context = {
                'ACCOUNT_CONTEXT': f"""Account Type: {account_type_str}
Balance: ${account.balance:.2f}
Equity: ${account.equity:.2f}
Leverage: 1:{account.leverage}
Currency: {account.currency}
Minimum Lot: {account.min_lot}
Lot Step: {account.lot_step}""",
                'ACCOUNT_TYPE': account_type_str,
                'MIN_LOT': str(account.min_lot),
                'MAX_LOT': str(account.max_lot),
                'LOT_STEP': str(account.lot_step),
                'RISK_PER_TRADE': f"{risk_settings['risk_per_trade']:.0%}",
                'MAX_DAILY_RISK': f"{risk_settings['max_daily_risk']:.0%}",
                'MIN_RRR': f"1:{risk_settings['min_rrr']:.1f}" if risk_settings['min_rrr'] >= 1 else str(risk_settings['min_rrr']),
                'TARGET_WINRATE': f"{risk_settings['target_winrate']:.0%}",
                'MAX_CONSECUTIVE_LOSSES': str(risk_settings['max_consecutive_losses'])
            }
            
            return context
        
        except Exception as e:
            logger.error(f"Failed to get account context: {e}")
            return {
                'ACCOUNT_CONTEXT': 'Error loading account information',
                'ACCOUNT_TYPE': 'normal',
                'MIN_LOT': '0.01',
                'MAX_LOT': '100.0',
                'LOT_STEP': '0.01',
                'RISK_PER_TRADE': '2%',
                'MAX_DAILY_RISK': '4%',
                'MIN_RRR': '2.0',
                'TARGET_WINRATE': '40%',
                'MAX_CONSECUTIVE_LOSSES': '4'
            }
    
    def _substitute_prompt_variables(self, prompt: str, context: dict) -> str:
        """Substitute template variables dalam prompt."""
        result = prompt
        for key, value in context.items():
            result = result.replace(f'{{{{{key}}}}}', str(value))
        return result


# Singleton instance
_prompt_templates_instance = None

def get_prompt_templates() -> PromptTemplates:
    """Get global PromptTemplates instance (singleton)."""
    global _prompt_templates_instance
    if _prompt_templates_instance is None:
        _prompt_templates_instance = PromptTemplates()
    return _prompt_templates_instance