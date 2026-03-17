"""
ThothMind Trading Challenge - Strategy Module
==============================================
MOMENTUM-CONTINUATION strategy for highly volatile assets (≥20% 24h change).

KEY INSIGHT: Assets that have already moved 20%+ in 24 hours are momentum plays.
We should trade WITH the existing momentum, not against it.

Strategy Principles:
1. Trade WITH the trend (momentum continuation)
2. Use volume to confirm moves
3. Enter early in momentum, not late
4. Wider stops for volatile assets
5. Simple is better - fewer conflicting indicators
"""
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

import config

logger = logging.getLogger(__name__)


class Signal(Enum):
    """Trading signal types"""
    STRONG_BUY = 2
    BUY = 1
    NEUTRAL = 0
    SELL = -1
    STRONG_SELL = -2


@dataclass
class MomentumAnalysis:
    """Analysis result for a ticker"""
    ticker: str
    current_price: float
    change_24h_pct: float
    
    # Momentum metrics
    short_momentum: float = 0.0    # Last 30 min momentum
    medium_momentum: float = 0.0   # Last 2 hour momentum
    volume_ratio: float = 1.0      # Current vs average volume
    trend_strength: float = 0.0    # How strong is the current trend
    
    # Price action
    is_making_new_highs: bool = False
    is_making_new_lows: bool = False
    distance_from_high: float = 0.0  # How far from recent high (%)
    distance_from_low: float = 0.0   # How far from recent low (%)
    
    # ATR for volatility-adjusted stops
    atr_pct: float = 0.0
    
    # Final scores
    long_score: float = 0.0
    short_score: float = 0.0
    signal: Signal = Signal.NEUTRAL
    confidence: float = 0.0
    
    def __repr__(self):
        return (f"MomentumAnalysis({self.ticker}: 24h={self.change_24h_pct:+.1f}%, "
                f"signal={self.signal.name}, conf={self.confidence:.2f})")


class MomentumAnalyzer:
    """
    Momentum-focused analysis engine.
    Designed for highly volatile assets that have already moved 20%+.
    """
    
    def __init__(self):
        self.short_period = 30    # 30 minute momentum
        self.medium_period = 120  # 2 hour momentum
        self.vol_period = 60      # Volume average period
        self.atr_period = 14      # ATR calculation period
    
    def calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return np.full(len(prices), np.nan)
        
        alpha = 2 / (period + 1)
        ema = np.zeros(len(prices))
        ema[:period] = np.nan
        ema[period - 1] = np.mean(prices[:period])
        
        for i in range(period, len(prices)):
            ema[i] = alpha * prices[i] + (1 - alpha) * ema[i - 1]
        
        return ema
    
    def calculate_atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """Calculate Average True Range as percentage of price"""
        if len(closes) < period + 1:
            return 2.0  # Default 2% ATR
        
        tr_values = []
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_prev_close = abs(highs[i] - closes[i-1])
            low_prev_close = abs(lows[i] - closes[i-1])
            tr = max(high_low, high_prev_close, low_prev_close)
            tr_values.append(tr)
        
        if len(tr_values) < period:
            return 2.0
        
        atr = np.mean(tr_values[-period:])
        atr_pct = (atr / closes[-1]) * 100
        return atr_pct
    
    def calculate_momentum(self, prices: np.ndarray, period: int) -> float:
        """Calculate momentum as percentage change over period"""
        if len(prices) < period + 1:
            return 0.0
        
        start_price = prices[-period-1]
        end_price = prices[-1]
        
        if start_price == 0:
            return 0.0
        
        return ((end_price - start_price) / start_price) * 100
    
    def calculate_volume_ratio(self, volumes: np.ndarray, period: int = 60) -> float:
        """Calculate current volume vs average"""
        if len(volumes) < period + 1:
            return 1.0
        
        avg_volume = np.mean(volumes[-period-1:-1])
        current_volume = volumes[-1]
        
        if avg_volume == 0:
            return 1.0
        
        return current_volume / avg_volume
    
    def check_price_action(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, lookback: int = 60) -> Dict:
        """Analyze recent price action"""
        if len(closes) < lookback:
            return {
                'making_new_highs': False,
                'making_new_lows': False,
                'distance_from_high': 0.0,
                'distance_from_low': 0.0
            }
        
        recent_high = np.max(highs[-lookback:])
        recent_low = np.min(lows[-lookback:])
        current_price = closes[-1]
        
        # Check if making new highs/lows in the last few candles
        very_recent_high = np.max(highs[-10:])
        very_recent_low = np.min(lows[-10:])
        
        making_new_highs = very_recent_high >= recent_high * 0.998  # Within 0.2%
        making_new_lows = very_recent_low <= recent_low * 1.002
        
        # Distance from extremes
        distance_from_high = ((recent_high - current_price) / current_price) * 100
        distance_from_low = ((current_price - recent_low) / current_price) * 100
        
        return {
            'making_new_highs': making_new_highs,
            'making_new_lows': making_new_lows,
            'distance_from_high': distance_from_high,
            'distance_from_low': distance_from_low
        }
    
    def calculate_trend_strength(self, prices: np.ndarray) -> float:
        """
        Calculate trend strength using price position relative to EMAs.
        Returns -1 to +1 (negative = downtrend, positive = uptrend)
        """
        if len(prices) < 50:
            return 0.0
        
        ema_fast = self.calculate_ema(prices, 9)
        ema_slow = self.calculate_ema(prices, 21)
        
        current_price = prices[-1]
        fast_val = ema_fast[-1]
        slow_val = ema_slow[-1]
        
        if np.isnan(fast_val) or np.isnan(slow_val):
            return 0.0
        
        # Score based on alignment
        score = 0.0
        
        # Price above both EMAs = bullish
        if current_price > fast_val > slow_val:
            score = 0.8
        elif current_price > fast_val and current_price > slow_val:
            score = 0.5
        elif current_price > slow_val:
            score = 0.2
        # Price below both EMAs = bearish  
        elif current_price < fast_val < slow_val:
            score = -0.8
        elif current_price < fast_val and current_price < slow_val:
            score = -0.5
        elif current_price < slow_val:
            score = -0.2
        
        return score
    
    def analyze_ticker(
        self,
        ticker: str,
        history: List[List],
        current_data: Dict,
        change_24h_pct: float
    ) -> MomentumAnalysis:
        """
        Perform momentum-focused analysis.
        Key principle: Trade WITH the momentum direction.
        """
        analysis = MomentumAnalysis(
            ticker=ticker,
            current_price=current_data.get('close', 0),
            change_24h_pct=change_24h_pct
        )
        
        if not history or len(history) < 100:
            logger.warning(f"{ticker}: Insufficient history ({len(history) if history else 0} candles)")
            return analysis
        
        # Extract price arrays
        try:
            closes = np.array([candle[4] for candle in history], dtype=float)
            highs = np.array([candle[2] for candle in history], dtype=float)
            lows = np.array([candle[3] for candle in history], dtype=float)
            volumes = np.array([candle[5] for candle in history], dtype=float)
        except (IndexError, TypeError) as e:
            logger.error(f"{ticker}: Error extracting data: {e}")
            return analysis
        
        # Calculate momentum at different timeframes
        analysis.short_momentum = self.calculate_momentum(closes, self.short_period)
        analysis.medium_momentum = self.calculate_momentum(closes, self.medium_period)
        
        # Volume analysis
        analysis.volume_ratio = self.calculate_volume_ratio(volumes, self.vol_period)
        
        # ATR for volatility
        analysis.atr_pct = self.calculate_atr(highs, lows, closes, self.atr_period)
        
        # Price action
        price_action = self.check_price_action(highs, lows, closes, 60)
        analysis.is_making_new_highs = price_action['making_new_highs']
        analysis.is_making_new_lows = price_action['making_new_lows']
        analysis.distance_from_high = price_action['distance_from_high']
        analysis.distance_from_low = price_action['distance_from_low']
        
        # Trend strength
        analysis.trend_strength = self.calculate_trend_strength(closes)
        
        # Calculate scores based on MOMENTUM CONTINUATION
        analysis.long_score, analysis.short_score = self._calculate_scores(analysis)
        
        # Determine final signal
        analysis.signal, analysis.confidence = self._determine_signal(analysis)
        
        return analysis
    
    def _calculate_scores(self, analysis: MomentumAnalysis) -> Tuple[float, float]:
        """
        Calculate long/short scores based on momentum continuation principle.
        
        Key insight: If 24h change is positive, we have a LONG BIAS.
                    If 24h change is negative, we have a SHORT BIAS.
        """
        long_score = 0.0
        short_score = 0.0
        
        # =====================================================================
        # COMPONENT 1: 24h Trend Direction (MOST IMPORTANT - 35% weight)
        # Trade WITH the existing momentum
        # =====================================================================
        if analysis.change_24h_pct > 30:
            long_score += 0.35 * 1.0
        elif analysis.change_24h_pct > 20:
            long_score += 0.35 * 0.8
        elif analysis.change_24h_pct < -30:
            short_score += 0.35 * 1.0
        elif analysis.change_24h_pct < -20:
            short_score += 0.35 * 0.8
        
        # =====================================================================
        # COMPONENT 2: Recent Momentum Confirmation (25% weight)
        # Short-term momentum should align with 24h direction
        # =====================================================================
        # Short-term momentum (last 30 min)
        if analysis.short_momentum > 1.0:  # Strong recent upward momentum
            long_score += 0.15 * min(analysis.short_momentum / 3, 1.0)
        elif analysis.short_momentum < -1.0:  # Strong recent downward momentum
            short_score += 0.15 * min(abs(analysis.short_momentum) / 3, 1.0)
        
        # Medium-term momentum (last 2 hours)
        if analysis.medium_momentum > 2.0:
            long_score += 0.10 * min(analysis.medium_momentum / 5, 1.0)
        elif analysis.medium_momentum < -2.0:
            short_score += 0.10 * min(abs(analysis.medium_momentum) / 5, 1.0)
        
        # =====================================================================
        # COMPONENT 3: Volume Confirmation (20% weight)
        # High volume confirms the move is real
        # =====================================================================
        if analysis.volume_ratio > 2.0:
            # High volume - confirms whatever direction price is moving
            if analysis.short_momentum > 0:
                long_score += 0.20 * min(analysis.volume_ratio / 3, 1.0)
            elif analysis.short_momentum < 0:
                short_score += 0.20 * min(analysis.volume_ratio / 3, 1.0)
        elif analysis.volume_ratio > 1.2:
            if analysis.short_momentum > 0:
                long_score += 0.10 * min(analysis.volume_ratio / 2, 0.8)
            elif analysis.short_momentum < 0:
                short_score += 0.10 * min(analysis.volume_ratio / 2, 0.8)
        
        # =====================================================================
        # COMPONENT 4: Price Action (15% weight)
        # Making new highs/lows shows trend continuation
        # =====================================================================
        if analysis.is_making_new_highs and analysis.change_24h_pct > 0:
            long_score += 0.15 * 1.0
        elif analysis.is_making_new_lows and analysis.change_24h_pct < 0:
            short_score += 0.15 * 1.0
        
        # Buying the dip in uptrend (close to recent low but 24h is positive)
        if analysis.change_24h_pct > 20 and analysis.distance_from_low < 2.0:
            long_score += 0.10
        # Selling the bounce in downtrend
        if analysis.change_24h_pct < -20 and analysis.distance_from_high < 2.0:
            short_score += 0.10
        
        # =====================================================================
        # COMPONENT 5: Trend Alignment (5% weight)
        # =====================================================================
        if analysis.trend_strength > 0.5:
            long_score += 0.05 * analysis.trend_strength
        elif analysis.trend_strength < -0.5:
            short_score += 0.05 * abs(analysis.trend_strength)
        
        return long_score, short_score
    
    def _determine_signal(self, analysis: MomentumAnalysis) -> Tuple[Signal, float]:
        """
        Determine final signal.
        
        CRITICAL: Only trade when direction is clear.
        CRITICAL: Don't trade against the 24h momentum unless very strong reversal.
        """
        long_score = analysis.long_score
        short_score = analysis.short_score
        
        # Safety check: Don't trade opposite to 24h momentum unless overwhelming evidence
        if analysis.change_24h_pct > 20 and short_score > long_score:
            # Would be shorting an up-mover - need much stronger signal
            if short_score < long_score + 0.3:
                return Signal.NEUTRAL, 0.0
        
        if analysis.change_24h_pct < -20 and long_score > short_score:
            # Would be longing a down-mover - need much stronger signal
            if long_score < short_score + 0.3:
                return Signal.NEUTRAL, 0.0
        
        # Determine signal based on score difference
        score_diff = long_score - short_score
        max_score = max(long_score, short_score)
        
        if score_diff > 0.3 and long_score > 0.4:
            return Signal.STRONG_BUY, min(long_score, 1.0)
        elif score_diff > 0.15 and long_score > 0.35:
            return Signal.BUY, min(long_score * 0.9, 0.9)
        elif score_diff < -0.3 and short_score > 0.4:
            return Signal.STRONG_SELL, min(short_score, 1.0)
        elif score_diff < -0.15 and short_score > 0.35:
            return Signal.SELL, min(short_score * 0.9, 0.9)
        else:
            return Signal.NEUTRAL, 0.0


class TradingStrategy:
    """
    Main trading strategy for momentum continuation on volatile assets.
    """
    
    def __init__(self):
        self.analyzer = MomentumAnalyzer()
        self.state = {}
        self.position_entry_time = None
        self.position_peak_pnl = 0.0
        self.last_trade_minute = -999
        self.trades_today = 0
        self.max_trades_per_day = config.MAX_TRADES_PER_DAY
    
    def reset(self):
        """Reset strategy state"""
        self.state = {}
        self.position_entry_time = None
        self.position_peak_pnl = 0.0
        self.last_trade_minute = -999
        self.trades_today = 0
        logger.info("Strategy state reset")
    
    def start_day(self, day: int, date: str, initial_balance: float):
        """Called at start of trading day"""
        self.state['day'] = day
        self.state['date'] = date
        self.state['initial_balance'] = initial_balance
        self.position_peak_pnl = 0.0
        self.last_trade_minute = -999
        self.trades_today = 0
        logger.info(f"Day {day} ({date}) started with balance: ${initial_balance:.2f}")
    
    def end_day(self, day: int, final_balance: float, daily_pnl: float):
        """Called at end of trading day"""
        pnl_pct = (daily_pnl / self.state.get('initial_balance', 1000)) * 100
        logger.info(f"Day {day} ended. Final: ${final_balance:.2f}, PnL: ${daily_pnl:.2f} ({pnl_pct:+.2f}%)")
    
    def decide(self, tick_data: Dict) -> Dict[str, Any]:
        """
        Main decision function called every tick.
        """
        position = tick_data.get('position', {})
        account = tick_data.get('account', {})
        market_data = tick_data.get('market_data', {})
        history = tick_data.get('history', {})
        qualifying_tickers = tick_data.get('qualifying_tickers', [])
        minutes_remaining = tick_data.get('minutes_remaining', 0)
        minute_of_day = tick_data.get('minute_of_day', 0)
        
        has_position = position.get('is_open', False)
        
        if has_position:
            result = self._manage_position(position, account, market_data, history, minutes_remaining)
            if result.get('action') == 'CLOSE':
                self.last_trade_minute = minute_of_day
                self.trades_today += 1
            return result
        else:
            result = self._find_entry(
                account, market_data, history, qualifying_tickers, minutes_remaining, minute_of_day
            )
            if result.get('action') in ['OPEN_LONG', 'OPEN_SHORT']:
                self.last_trade_minute = minute_of_day
            return result
    
    def _manage_position(
        self,
        position: Dict,
        account: Dict,
        market_data: Dict,
        history: Dict,
        minutes_remaining: int
    ) -> Dict[str, Any]:
        """
        Manage existing position with volatility-aware exits.
        """
        ticker = position.get('ticker', '')
        side = position.get('side', '')
        unrealized_pnl_pct = position.get('unrealized_pnl_pct', 0.0)
        unrealized_pnl = position.get('unrealized_pnl', 0.0)
        leverage = position.get('leverage', 3)
        
        # Track peak PnL for trailing stop
        if unrealized_pnl > self.position_peak_pnl:
            self.position_peak_pnl = unrealized_pnl
        
        # Get ATR for volatility-adjusted stops
        atr_pct = 2.0  # Default
        if ticker in history:
            try:
                closes = np.array([c[4] for c in history[ticker]], dtype=float)
                highs = np.array([c[2] for c in history[ticker]], dtype=float)
                lows = np.array([c[3] for c in history[ticker]], dtype=float)
                atr_pct = self.analyzer.calculate_atr(highs, lows, closes, 14)
            except:
                pass
        
        # Volatility-adjusted stop loss (wider for volatile assets)
        # Base stop is config value, but scale with ATR
        dynamic_stop = max(config.STOP_LOSS_PCT, atr_pct * leverage * 1.5)
        dynamic_stop = min(dynamic_stop, 20.0)  # Cap at 20%
        
        close_reason = None
        
        # 1. Stop loss (volatility-adjusted)
        if unrealized_pnl_pct < -dynamic_stop:
            close_reason = f"Stop loss at {unrealized_pnl_pct:.2f}% (dynamic stop: {dynamic_stop:.1f}%)"
        
        # 2. Take profit
        elif unrealized_pnl_pct > config.TAKE_PROFIT_PCT:
            close_reason = f"Take profit at {unrealized_pnl_pct:.2f}%"
        
        # 3. Trailing stop (only after significant profit)
        elif self.position_peak_pnl > 0 and unrealized_pnl_pct > 10.0:
            # Trail at 50% of peak profit
            trail_level = self.position_peak_pnl * 0.5
            if unrealized_pnl < trail_level:
                close_reason = f"Trailing stop: PnL {unrealized_pnl:.2f} below trail level {trail_level:.2f}"
        
        # 4. End of day
        if minutes_remaining < config.MIN_MINUTES_BEFORE_EOD:
            # If profitable, take it; if losing, let it ride a bit more
            if unrealized_pnl_pct > 0 or minutes_remaining < 30:
                close_reason = f"EOD approaching ({minutes_remaining} min)"
        
        # 5. Momentum reversal check
        if ticker in history and ticker in market_data and not close_reason:
            analysis = self.analyzer.analyze_ticker(
                ticker,
                history[ticker],
                market_data[ticker],
                market_data[ticker].get('change_24h_pct', 0)
            )
            
            # Strong reversal signal against position
            if side == 'LONG' and analysis.signal in [Signal.STRONG_SELL, Signal.SELL]:
                if analysis.confidence > 0.6 and analysis.short_momentum < -2.0:
                    close_reason = f"Momentum reversal (short_mom: {analysis.short_momentum:.2f}%)"
            elif side == 'SHORT' and analysis.signal in [Signal.STRONG_BUY, Signal.BUY]:
                if analysis.confidence > 0.6 and analysis.short_momentum > 2.0:
                    close_reason = f"Momentum reversal (short_mom: {analysis.short_momentum:.2f}%)"
        
        if close_reason:
            logger.info(f"Closing {side} {ticker}: {close_reason}")
            return {'action': 'CLOSE', 'reason': close_reason}
        
        return {
            'action': 'HOLD',
            'reason': f"Holding {side} {ticker} at {unrealized_pnl_pct:+.2f}%"
        }
    
    def _find_entry(
        self,
        account: Dict,
        market_data: Dict,
        history: Dict,
        qualifying_tickers: List[str],
        minutes_remaining: int,
        minute_of_day: int
    ) -> Dict[str, Any]:
        """
        Find best entry opportunity using momentum continuation.
        """
        # Don't enter too close to EOD
        if minutes_remaining < config.MIN_MINUTES_BEFORE_EOD:
            return {'action': 'HOLD', 'reason': f"Too close to EOD ({minutes_remaining} min)"}
        
        # Cooldown check
        cooldown = config.TRADE_COOLDOWN_MINUTES
        if minute_of_day - self.last_trade_minute < cooldown:
            remaining = cooldown - (minute_of_day - self.last_trade_minute)
            return {'action': 'HOLD', 'reason': f"Cooldown ({remaining} min remaining)"}
        
        # Daily trade limit
        if self.trades_today >= self.max_trades_per_day:
            return {'action': 'HOLD', 'reason': f"Daily limit reached ({self.max_trades_per_day})"}
        
        # Analyze all qualifying tickers
        analyses = []
        for ticker in qualifying_tickers:
            if ticker not in history or ticker not in market_data:
                continue
            
            analysis = self.analyzer.analyze_ticker(
                ticker,
                history[ticker],
                market_data[ticker],
                market_data[ticker].get('change_24h_pct', 0)
            )
            analyses.append(analysis)
        
        if not analyses:
            return {'action': 'HOLD', 'reason': 'No tickers with sufficient data'}
        
        # Find best candidates
        long_candidates = [a for a in analyses if a.signal in [Signal.STRONG_BUY, Signal.BUY]]
        short_candidates = [a for a in analyses if a.signal in [Signal.STRONG_SELL, Signal.SELL]]
        
        best_long = max(long_candidates, key=lambda x: x.long_score, default=None)
        best_short = max(short_candidates, key=lambda x: x.short_score, default=None)
        
        # Pick the stronger signal
        candidate = None
        action = None
        
        if best_long and best_short:
            if best_long.long_score > best_short.short_score:
                candidate = best_long
                action = 'OPEN_LONG'
            else:
                candidate = best_short
                action = 'OPEN_SHORT'
        elif best_long:
            candidate = best_long
            action = 'OPEN_LONG'
        elif best_short:
            candidate = best_short
            action = 'OPEN_SHORT'
        
        # Check confidence threshold
        if candidate and candidate.confidence >= config.MIN_CONFIDENCE:
            leverage = self._calculate_leverage(candidate)
            size_pct = self._calculate_size(candidate, account)
            
            logger.info(
                f"Opening {action} {candidate.ticker}: "
                f"24h={candidate.change_24h_pct:+.1f}%, "
                f"short_mom={candidate.short_momentum:+.2f}%, "
                f"vol_ratio={candidate.volume_ratio:.2f}, "
                f"conf={candidate.confidence:.2f}, "
                f"lev={leverage}x, size={size_pct}%"
            )
            
            self.position_peak_pnl = 0.0
            
            return {
                'action': action,
                'ticker': candidate.ticker,
                'leverage': leverage,
                'size_pct': size_pct,
                'reason': f"Momentum: {candidate.signal.name}, 24h: {candidate.change_24h_pct:+.1f}%"
            }
        
        return {'action': 'HOLD', 'reason': 'No signals meet confidence threshold'}
    
    def _calculate_leverage(self, analysis: MomentumAnalysis) -> int:
        """
        Calculate leverage based on signal strength and volatility.
        More conservative for very volatile assets.
        """
        base_leverage = config.DEFAULT_LEVERAGE
        
        # Adjust for confidence
        if analysis.confidence > 0.85:
            leverage = base_leverage + 2
        elif analysis.confidence > 0.7:
            leverage = base_leverage + 1
        else:
            leverage = base_leverage
        
        # REDUCE for extreme volatility
        if abs(analysis.change_24h_pct) > 50:
            leverage = max(leverage - 2, config.MIN_LEVERAGE)
        elif abs(analysis.change_24h_pct) > 35:
            leverage = max(leverage - 1, config.MIN_LEVERAGE)
        
        # Also reduce if ATR is very high
        if analysis.atr_pct > 3.0:
            leverage = max(leverage - 1, config.MIN_LEVERAGE)
        
        return min(leverage, config.MAX_LEVERAGE)
    
    def _calculate_size(self, analysis: MomentumAnalysis, account: Dict) -> int:
        """
        Calculate position size based on confidence and volatility.
        """
        if analysis.confidence > 0.85:
            size_pct = config.DEFAULT_SIZE_PCT
        elif analysis.confidence > 0.7:
            size_pct = int(config.DEFAULT_SIZE_PCT * 0.8)
        else:
            size_pct = int(config.DEFAULT_SIZE_PCT * 0.6)
        
        # Reduce size for very volatile assets
        if abs(analysis.change_24h_pct) > 40:
            size_pct = int(size_pct * 0.8)
        
        return min(max(size_pct, config.MIN_SIZE_PCT), config.MAX_SIZE_PCT)
