import asyncio
from typing import Dict, Any
from decimal import Decimal, ROUND_DOWN
from .agents import ProAgent, ConAgent, get_market_narrative
from .rag import RAGSystem
from .llm_resilience import call_llm_with_retry
from .audit_log import AuditLogger
from .notifications import send_telegram_alert
from core.config import ConfigManager
from core.database import TradeDatabase
from core.judge_monitor import get_judge_monitor
from datetime import datetime, timedelta
import time

class TheJudge:
    def __init__(self):
        self.rag = RAGSystem()
        self.pro_agent = ProAgent()
        self.con_agent = ConAgent()
        self.audit_logger = AuditLogger()
        self.config = ConfigManager.load_config()
        self.db = TradeDatabase()
        self.monitor = get_judge_monitor()  # Real-time GUI monitor
        
        # Updated Weights (Removing Hardcoded RAG Score, giving more power to Debate)
        self.WEIGHT_TIER_1 = Decimal('0.30')  # Structure/Trend Check
        self.WEIGHT_TIER_3 = Decimal('0.70')  # The Great Debate
        self.EXECUTION_THRESHOLD = Decimal('0.65') # Slightly lowered since Debate is more nuanced
        
        # STRICT RISK MANAGEMENT (Production-Ready)
        self.RISK_PERCENT = Decimal('0.02')  # Fixed 2% risk per trade
        self.MAX_RISK_PERCENT = Decimal('0.05')  # Emergency cap: 5% max

    async def evaluate(self, data: Any) -> Dict[str, Any]:
        start_time = time.perf_counter()
        
        # --- 0. Cooldown Check ---
        cooldown_mins = self.config.get('trading', {}).get('cooldown_minutes', 15)
        last_trade = self.db.get_last_trade_time(data.symbol)
        
        if last_trade:
            # Ensure timezone awareness compatibility
            now = datetime.now()
            # If last_trade is naive, assume local/server time same as now
            if last_trade.tzinfo is None:
                elapsed = now - last_trade
            else:
                elapsed = now.astimezone() - last_trade.astimezone()
                
            if elapsed < timedelta(minutes=cooldown_mins):
                wait_time = int(cooldown_mins - elapsed.total_seconds() / 60)
                return self._create_signal("HOLD", Decimal('0.0'), f"COOLDOWN ACTIVE: {wait_time}m remaining")

        # 1. Tier 1: Basic Structure Check (Filter)
        tier_1_score, tier_1_reason = self._evaluate_tier_1(data)
        if tier_1_score == Decimal('-1'):
            return self._create_signal("HOLD", Decimal('0.0'), f"Tier 1 Veto: {tier_1_reason}")

        # 2. Tier 2: RAG Context Retrieval (The Brain)
        # RAG is now digested by Pro/Con agents, so we don't score it separately here.
        history_context = self.rag.query_similar_history(data)
        concept_query = "Trend Following Rules" if tier_1_score > 0 else "Reversal Rules"
        concept_context = self.rag.query_concepts(concept_query)
        
        rag_packet = {
            "history": history_context,
            "concepts": concept_context
        }

        # 3. Tier 3: Agent Debate (The Soul)
        narrative = await get_market_narrative(data.symbol)
        
        pro_arg = await self.pro_agent.argue(data, narrative, rag_packet)
        con_arg = await self.con_agent.argue(data, narrative, rag_packet)
        
        # REAL LLM ARBITRATION
        tier_3_score, tier_3_reason = await self._arbitrate_agents(pro_arg, con_arg, data)
        # Ensure score is Decimal
        try:
            tier_3_score = Decimal(str(tier_3_score))
        except:
            tier_3_score = Decimal('0.5')

        final_score = (
            (tier_1_score * self.WEIGHT_TIER_1) +
            (tier_3_score * self.WEIGHT_TIER_3)
        )
        
        is_buy_signal = final_score >= self.EXECUTION_THRESHOLD
        
        if is_buy_signal:
            # Convert to Decimal for precision
            price = Decimal(str(data.price))
            low = Decimal(str(data.low))
            
            sl = low * Decimal('0.99')
            tp = price * Decimal('1.02')
            
            # --- Dynamic Lot Calculation dengan Account Awareness ---
            lot = self._calculate_safe_lot(
                balance=Decimal(str(data.balance)),
                entry_price=price,
                sl_price=sl,
                min_lot=Decimal(str(data.min_lot)),
                step_lot=Decimal(str(data.step_lot)),
                symbol=data.symbol,
                account_id=getattr(data, 'account_id', 'default')
            )
            
            # Prepare Signal
            signal = self._create_signal(
                "BUY", 
                lot, 
                reason=f"Score: {final_score:.2f} | Judge: {tier_3_reason}",
                sl=sl, tp=tp, score=final_score
            )
            
            # Audit Log (Async or fast sync)
            self.audit_logger.log_decision(
                symbol=data.symbol,
                timeframe=getattr(data, 'timeframe', 'M1'), # Default to M1 if missing
                decision="BUY",
                market_data=data,
                tier_1_result=(tier_1_score, tier_1_reason),
                tier_3_result=(tier_3_score, tier_3_reason),
                final_score=float(final_score),
                pro_response=pro_arg,
                con_response=con_arg,
                execution_details={'lot': float(lot), 'sl': float(sl), 'tp': float(tp)},
                duration_ms=(time.perf_counter() - start_time) * 1000
            )
            
            # Record untuk GUI real-time monitor
            self.monitor.record_evaluation({
                'symbol': data.symbol,
                'timeframe': getattr(data, 'timeframe', 'M1'),
                'action': 'BUY',
                'confidence_score': float(final_score),
                'debate_winner': 'PRO' if tier_3_score > 0.5 else 'CON',
                'pro_confidence': float(self._extract_confidence(pro_arg)),
                'con_confidence': float(self._extract_confidence(con_arg)),
                'tier1_contribution': float(tier_1_score * self.WEIGHT_TIER_1),
                'tier3_contribution': float(tier_3_score * self.WEIGHT_TIER_3),
                'veto_active': tier_1_score == Decimal('-1'),
                'veto_reason': tier_1_reason if tier_1_score == Decimal('-1') else None,
                'reasoning': tier_3_reason,
                'entry_price': float(data.price),
                'stop_loss': float(sl),
                'take_profit': float(tp)
            })

            # Send Telegram Alert (Non-blocking)
            msg = (
                f"🚀 **BUY SIGNAL: {data.symbol}**\n"
                f"Score: `{final_score:.2f}`\n"
                f"Reason: _{tier_3_reason}_\n"
                f"SL: `{sl}` | TP: `{tp}`"
            )
            asyncio.create_task(send_telegram_alert(msg))

            return signal
        else:
            signal = self._create_signal(
                "HOLD", 
                Decimal('0.0'), 
                reason=f"Score {final_score:.2f} < {self.EXECUTION_THRESHOLD} | Judge: {tier_3_reason}",
                score=final_score
            )
            
            # Audit Log for HOLD
            self.audit_logger.log_decision(
                symbol=data.symbol,
                timeframe=getattr(data, 'timeframe', 'M1'),
                decision="HOLD",
                market_data=data,
                tier_1_result=(tier_1_score, tier_1_reason),
                tier_3_result=(tier_3_score, tier_3_reason),
                final_score=float(final_score),
                pro_response=pro_arg,
                con_response=con_arg,
                duration_ms=(time.perf_counter() - start_time) * 1000
            )
            
            # Record untuk GUI real-time monitor
            self.monitor.record_evaluation({
                'symbol': data.symbol,
                'timeframe': getattr(data, 'timeframe', 'M1'),
                'action': 'HOLD',
                'confidence_score': float(final_score),
                'debate_winner': 'NEUTRAL',
                'pro_confidence': float(self._extract_confidence(pro_arg)),
                'con_confidence': float(self._extract_confidence(con_arg)),
                'tier1_contribution': float(tier_1_score * self.WEIGHT_TIER_1),
                'tier3_contribution': float(tier_3_score * self.WEIGHT_TIER_3),
                'veto_active': tier_1_score == Decimal('-1'),
                'veto_reason': tier_1_reason if tier_1_score == Decimal('-1') else None,
                'reasoning': f"Score {final_score:.2f} below threshold {self.EXECUTION_THRESHOLD}",
                'entry_price': float(data.price),
                'stop_loss': 0.0,
                'take_profit': 0.0
            })
            
            return signal

    def _evaluate_tier_1(self, data) -> (Decimal, str):
        """
        Tier 1: Mathematical Analysis menggunakan Chart Data.
        Evaluates trend strength dan market structure.
        """
        try:
            from core.chart_manager import get_chart_manager
            
            symbol = getattr(data, 'symbol', None)
            timeframe = getattr(data, 'timeframe', 'H1')
            
            if not symbol:
                # Fallback ke data lama (MA)
                if data.ma_fast and data.ma_slow:
                    if data.ma_fast > data.ma_slow:
                        return Decimal('1.0'), "Bullish Structure (Legacy)"
                    else:
                        return Decimal('-1.0'), "Bearish Structure (Legacy)"
                return Decimal('0.5'), "Neutral/No Data"
            
            # Get chart data
            chart_manager = get_chart_manager()
            chart_data = chart_manager.get_chart_data(symbol, timeframe)
            
            if not chart_data.get('available', False):
                # No chart data, use legacy
                if data.ma_fast and data.ma_slow:
                    if data.ma_fast > data.ma_slow:
                        return Decimal('1.0'), "Bullish Structure (Legacy)"
                    else:
                        return Decimal('-1.0'), "Bearish Structure (Legacy)"
                return Decimal('0.5'), "Neutral/No Chart Data"
            
            indicators = chart_data.get('indicators', {})
            
            # Check trend
            trend = indicators.get('trend', 'neutral')
            rsi = indicators.get('rsi_14', 50)
            bb = indicators.get('bollinger', {})
            bb_position = bb.get('position', 0.5)
            
            # Scoring logic
            score = Decimal('0.5')
            reasons = []
            
            # Trend component (40%)
            trend_scores = {
                'strong_bullish': Decimal('0.4'),
                'bullish': Decimal('0.3'),
                'neutral': Decimal('0.0'),
                'bearish': Decimal('-0.3'),
                'strong_bearish': Decimal('-0.4')
            }
            trend_score = trend_scores.get(trend, Decimal('0.0'))
            score += trend_score
            if trend != 'neutral':
                reasons.append(f"Trend: {trend}")
            
            # RSI component (20%)
            if rsi > 70:
                score -= Decimal('0.2')
                reasons.append("RSI Overbought")
            elif rsi < 30:
                score += Decimal('0.2')
                reasons.append("RSI Oversold")
            elif 40 <= rsi <= 60:
                score += Decimal('0.1')
                reasons.append("RSI Neutral")
            
            # Bollinger Position (20%)
            if bb_position > 0.8:
                score -= Decimal('0.2')
                reasons.append("Price near upper BB")
            elif bb_position < 0.2:
                score += Decimal('0.2')
                reasons.append("Price near lower BB")
            elif 0.4 <= bb_position <= 0.6:
                score += Decimal('0.1')
                reasons.append("Price in BB middle")
            
            # Structure levels (20%)
            structure = indicators.get('structure', {})
            current_price = indicators.get('current_price', 0)
            support = structure.get('support', 0)
            resistance = structure.get('resistance', 0)
            
            if support and resistance and current_price:
                range_size = resistance - support
                if range_size > 0:
                    position_in_range = (current_price - support) / range_size
                    if position_in_range < 0.3:
                        score += Decimal('0.2')
                        reasons.append("Near support")
                    elif position_in_range > 0.7:
                        score -= Decimal('0.2')
                        reasons.append("Near resistance")
            
            # Clamp score between -1 dan 1
            score = max(Decimal('-1.0'), min(Decimal('1.0'), score))
            
            reason = " | ".join(reasons) if reasons else "Neutral"
            
            # Check untuk hard veto
            if score < Decimal('-0.7'):
                return Decimal('-1.0'), f"Strong Bearish Veto: {reason}"
            
            return score, f"Tier 1: {reason}"
        
        except Exception as e:
            logger.error(f"Tier 1 evaluation error: {e}")
            # Fallback ke legacy
            if data.ma_fast and data.ma_slow:
                if data.ma_fast > data.ma_slow:
                    return Decimal('1.0'), "Bullish Structure (Fallback)"
                else:
                    return Decimal('-1.0'), "Bearish Structure (Fallback)"
            return Decimal('0.5'), "Neutral/Error"

    async def _arbitrate_agents(self, pro: str, con: str, data: Any) -> tuple[Decimal, str]:
        """
        The Judge listens to both agents and decides.
        Returns: (Score 0.0-1.0, Reason)
        """
        # Get chart data untuk enrichment
        chart_context = ""
        try:
            from core.chart_manager import get_chart_manager
            symbol = getattr(data, 'symbol', None)
            timeframe = getattr(data, 'timeframe', 'H1')
            
            if symbol:
                chart_manager = get_chart_manager()
                chart_data = chart_manager.get_chart_data(symbol, timeframe)
                
                if chart_data.get('available'):
                    indicators = chart_data.get('indicators', {})
                    bb = indicators.get('bollinger', {})
                    structure = indicators.get('structure', {})
                    
                    chart_context = f"""
                    TECHNICAL CONTEXT (dari Chart Analysis):
                    - Trend: {indicators.get('trend', 'unknown')}
                    - RSI: {indicators.get('rsi_14', 'N/A'):.1f}
                    - SMA 20: {indicators.get('sma_20', 'N/A'):.5f}
                    - ATR 14: {indicators.get('atr_14', 'N/A'):.5f}
                    - Bollinger: Upper={bb.get('upper', 'N/A'):.5f}, Lower={bb.get('lower', 'N/A'):.5f}
                    - Support: {structure.get('support', 'N/A'):.5f}
                    - Resistance: {structure.get('resistance', 'N/A'):.5f}
                    """
        except Exception as e:
            logger.debug(f"Could not load chart context: {e}")
        
        config = self.pro_agent.config # Borrow config
        prompt = f"""
        ROLE:
        You are the Head of Trading (The Judge). You must decide whether to Execute (BUY/SELL) or WAIT based on the arguments below.
        
        ARGUMENT 1 (THE PRO AGENT - GAS):
        "{pro}"
        
        ARGUMENT 2 (THE CON AGENT - BRAKE):
        "{con}"
        
        MARKET DATA:
        Price: {data.price} | RSI: {data.rsi} | Trend: {data.ma_trend}
        {chart_context}
        
        DECISION RULES:
        1. If Con Agent identifies a FATAL FLAW (e.g. Structure Resistance, Negative R:R), you MUST REJECT (Score < 0.5).
        2. If Pro Agent has a strong logic AND Con Agent only has minor concerns, you APPROVE (Score > 0.7).
        3. Consider Technical Context (Trend, RSI, BB) sebagai validasi tambahan.
        4. If both are weak, WAIT (Score 0.5).
        
        OUTPUT FORMAT:
        Score|Reason
        Example: 0.85|Valid Trend with Safe R:R.
        Example: 0.20|Rejected due to overhead resistance.
        
        Your Answer:
        """
        try:
            # Use resilient LLM call with retry logic and circuit breaker
            response = await call_llm_with_retry(
                self.pro_agent.llm.ainvoke,
                prompt,
                max_retries=3,
                timeout=30.0
            )
            content = response.content.strip()
            
            if "|" in content:
                score_str, reason = content.split("|", 1)
                return Decimal(score_str), reason.strip()
            else:
                return Decimal('0.5'), content[:50]
        except Exception as e:
            return Decimal('0.5'), f"Judge Error: {str(e)}"

    def _calculate_safe_lot(
        self, 
        balance: Decimal, 
        entry_price: Decimal, 
        sl_price: Decimal, 
        min_lot: Decimal, 
        step_lot: Decimal,
        symbol: str = '',
        account_id: str = 'default'
    ) -> Decimal:
        """
        Calculate Position Size based on account type dan risk settings.
        
        Features:
        - Account type detection (normal vs micro)
        - Proper lot alignment untuk micro accounts (0.1, 0.2, etc.)
        - Dynamic risk calculation based on account balance
        - RRR (Risk-Reward Ratio) validation
        - Positive Expectancy focus
        """
        try:
            from core.account_manager import get_account_manager
            
            account_manager = get_account_manager()
            account = account_manager.get_account(account_id)
            
            # Get risk settings based on mode (safe, balanced, aggressive, sniper)
            mode = getattr(self.config, 'trading_mode', 'balanced')
            risk_settings = account_manager.get_risk_settings(account_id, mode)
            
            # Use account-based values jika tersedia
            if account:
                min_lot = Decimal(str(account.min_lot))
                step_lot = Decimal(str(account.lot_step))
                risk_percent = Decimal(str(risk_settings['risk_per_trade']))
                min_rrr = risk_settings['min_rrr']
            else:
                # Fallback values
                risk_percent = self.RISK_PERCENT
                min_rrr = 2.0
            
            # Calculate risk amount
            risk_amount = balance * risk_percent
            
            # Calculate SL distance dalam pips/points
            price_diff = abs(entry_price - sl_price)
            if price_diff == 0:
                logger.warning("SL distance is zero, using minimum lot")
                return min_lot
            
            # Calculate raw lot size
            # Risk = Lot × SL_Distance × Pip_Value
            # Pip value varies by symbol (approximate)
            pip_value = self._estimate_pip_value(symbol)
            raw_lot = risk_amount / (price_diff * Decimal(str(pip_value)))
            
            # Account type specific handling
            if account and account.is_micro:
                # Micro account: Round to nearest 0.1
                # Example: 0.15 → 0.1, 0.25 → 0.3
                raw_lot = (raw_lot / Decimal('0.1')).quantize(Decimal('1'), rounding=ROUND_DOWN) * Decimal('0.1')
                logger.debug(f"Micro account lot adjustment: {raw_lot}")
            else:
                # Normal account: Round to step
                steps = (raw_lot / step_lot).quantize(Decimal('1'), rounding=ROUND_DOWN)
                raw_lot = steps * step_lot
            
            # Validate lot size
            is_valid, adjusted_lot = account_manager.validate_lot_size(float(raw_lot), account_id)
            raw_lot = Decimal(str(adjusted_lot))
            
            # Risk validation: Check if using minimum lot exceeds risk tolerance
            if raw_lot < min_lot:
                potential_risk_val = min_lot * price_diff * Decimal(str(pip_value))
                potential_risk_pct = potential_risk_val / balance
                
                max_risk = Decimal(str(risk_settings.get('max_daily_risk', 0.05)))
                
                if potential_risk_pct > max_risk:
                    logger.warning(
                        f"ABORT: Min lot risk ({potential_risk_pct:.2%}) exceeds max ({max_risk:.2%})"
                    )
                    return Decimal('0.0')  # ABORT trade
                
                raw_lot = min_lot
            
            # Clamp to min/max
            result = max(min_lot, min(Decimal(str(risk_settings.get('max_lot', 100))), raw_lot))
            
            logger.info(
                f"Lot calculation: Balance=${float(balance):.2f}, Risk={float(risk_percent):.1%}, "
                f"SL={float(price_diff):.5f}, Result={float(result):.2f} "
                f"({account.account_type if account else 'unknown'})"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Lot calculation error: {e}")
            # Fallback to minimum lot
            return min_lot
    
    def _estimate_pip_value(self, symbol: str) -> float:
        """Estimate pip value untuk symbol."""
        symbol_upper = symbol.upper() if symbol else ''
        
        # Forex pairs
        if 'JPY' in symbol_upper:
            return 1000.0  # JPY pairs: 0.01 movement = $10 per lot
        elif 'XAU' in symbol_upper or 'GOLD' in symbol_upper:
            return 100.0   # Gold
        elif 'XAG' in symbol_upper or 'SILVER' in symbol_upper:
            return 50.0    # Silver
        elif 'BTC' in symbol_upper:
            return 1.0     # Crypto
        else:
            return 100.0   # Standard forex pairs: 0.0001 = $10 per lot
        
        # Return with 2 decimal precision (standard for lot sizes)
        return result.quantize(Decimal('0.01'), rounding=ROUND_DOWN)

    def _validate_sl_tp(
        self, 
        entry_price: Decimal, 
        sl: Decimal, 
        tp: Decimal,
        is_buy: bool
    ) -> bool:
        """
        Validate SL/TP placement to prevent errors.
        
        Args:
            entry_price: Entry price
            sl: Stop Loss price
            tp: Take Profit price
            is_buy: True if BUY order, False if SELL
            
        Returns:
            True if valid, False otherwise
        """
        MIN_DISTANCE_PIPS = Decimal('10')  # Minimum 10 pips distance
        
        if is_buy:
            # For BUY: SL must be below entry, TP must be above
            if sl >= entry_price or tp <= entry_price:
                return False
            # Check minimum distance (assuming 1 pip = 0.0001 for Forex)
            if (entry_price - sl) < MIN_DISTANCE_PIPS * Decimal('0.0001'):
                return False
        else:
            # For SELL: SL must be above entry, TP must be below
            if sl <= entry_price or tp >= entry_price:
                return False
            if (sl - entry_price) < MIN_DISTANCE_PIPS * Decimal('0.0001'):
                return False
        
        return True

    def _create_signal(self, action, lot, reason, sl=Decimal('0.0'), tp=Decimal('0.0'), score=Decimal('0.0')):
        """
        Create trade signal with proper type conversion for API response.
        """
        return {
            "action": action,
            "lot_size": float(lot),  # Convert to float for JSON serialization
            "sl": float(sl),
            "tp": float(tp),
            "reason": reason,
            "confidence_score": float(score)
        }
    
    def _extract_confidence(self, agent_response: str) -> Decimal:
        """
        Extract confidence score dari agent response.
        Mencari angka di response (0.0 - 1.0).
        """
        try:
            # Cari pattern seperti "0.75", "75%", atau "confidence: 0.8"
            import re
            
            # Cari angka dengan format 0.XX
            match = re.search(r'0\.\d+', agent_response)
            if match:
                return Decimal(match.group())
            
            # Cari persentase XX%
            match = re.search(r'(\d+)%', agent_response)
            if match:
                return Decimal(match.group(1)) / 100
            
            return Decimal('0.5')  # Default
        except:
            return Decimal('0.5')
