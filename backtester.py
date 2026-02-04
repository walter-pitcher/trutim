"""
ThothMind Trading Challenge - Backtester
=========================================
Backtest the trading strategy against historical data.

This module simulates the exact trading environment described in Phase2.md:
- Trading window: 08:00 UTC - 24:00 UTC
- Eligible assets: Only tickers with ≥20% absolute 24h change
- One position at a time
- End of day forced close
- PnL calculation matching the challenge rules
"""
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import logging
import json

import config
from strategy import TradingStrategy

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Record of a completed trade"""
    ticker: str
    side: str  # LONG or SHORT
    entry_time: str
    entry_price: float
    exit_time: str
    exit_price: float
    size: float
    leverage: int
    pnl: float
    pnl_pct: float
    reason: str = ""


@dataclass
class Position:
    """Current open position"""
    ticker: str
    side: str
    entry_time: str
    entry_price: float
    size: float
    leverage: int
    
    def calculate_pnl(self, current_price: float) -> Tuple[float, float]:
        """Calculate unrealized PnL"""
        if self.side == 'LONG':
            pnl_pct = ((current_price - self.entry_price) / self.entry_price) * self.leverage * 100
        else:  # SHORT
            pnl_pct = ((self.entry_price - current_price) / self.entry_price) * self.leverage * 100
        
        pnl_dollar = self.size * (pnl_pct / 100)
        return pnl_dollar, pnl_pct


@dataclass
class DailyResult:
    """Results for a single trading day"""
    day: int
    date: str
    starting_balance: float
    ending_balance: float
    daily_pnl: float
    trades: List[Trade] = field(default_factory=list)
    
    @property
    def daily_return_pct(self) -> float:
        return (self.daily_pnl / self.starting_balance) * 100 if self.starting_balance > 0 else 0


@dataclass
class BacktestResult:
    """Complete backtest results"""
    initial_balance: float
    final_balance: float
    total_pnl: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    daily_results: List[DailyResult] = field(default_factory=list)
    all_trades: List[Trade] = field(default_factory=list)


class Backtester:
    """
    Backtesting engine that simulates the challenge environment.
    """
    
    def __init__(self, data_path: str = 'december_2025_dataset.npz'):
        self.data_path = data_path
        self.data: Dict[str, np.ndarray] = {}
        self.strategy = TradingStrategy()
        
        # State
        self.balance = config.INITIAL_BALANCE
        self.position: Optional[Position] = None
        self.trades: List[Trade] = []
        self.daily_results: List[DailyResult] = []
        self.equity_curve: List[float] = []
        
    def load_data(self):
        """Load the historical dataset"""
        logger.info(f"Loading data from {self.data_path}...")
        npz_data = np.load(self.data_path, allow_pickle=True)
        
        for key in npz_data.keys():
            self.data[key] = npz_data[key]
        
        logger.info(f"Loaded {len(self.data)} tickers")
        
        # Get date range
        sample_ticker = list(self.data.keys())[0]
        sample_data = self.data[sample_ticker]
        first_ts = sample_data['timestamp'][0]
        last_ts = sample_data['timestamp'][-1]
        
        logger.info(f"Date range: {first_ts} to {last_ts}")
    
    def get_candle_at_time(self, ticker: str, timestamp: np.datetime64) -> Optional[Dict]:
        """Get candle data for a specific timestamp"""
        if ticker not in self.data:
            return None
        
        ticker_data = self.data[ticker]
        mask = ticker_data['timestamp'] == timestamp
        
        if not np.any(mask):
            return None
        
        idx = np.where(mask)[0][0]
        candle = ticker_data[idx]
        
        return {
            'timestamp': str(candle['timestamp']),
            'open': float(candle['open']),
            'high': float(candle['high']),
            'low': float(candle['low']),
            'close': float(candle['close']),
            'volume': float(candle['volume'])
        }
    
    def get_history(self, ticker: str, end_timestamp: np.datetime64, minutes: int = 1440) -> List[List]:
        """Get historical candles for a ticker (last N minutes)"""
        if ticker not in self.data:
            return []
        
        ticker_data = self.data[ticker]
        
        # Find index of end timestamp
        mask = ticker_data['timestamp'] <= end_timestamp
        if not np.any(mask):
            return []
        
        end_idx = np.where(mask)[0][-1]
        start_idx = max(0, end_idx - minutes + 1)
        
        history = []
        for i in range(start_idx, end_idx + 1):
            candle = ticker_data[i]
            history.append([
                str(candle['timestamp']),
                float(candle['open']),
                float(candle['high']),
                float(candle['low']),
                float(candle['close']),
                float(candle['volume'])
            ])
        
        return history
    
    def calculate_24h_change(self, ticker: str, current_timestamp: np.datetime64) -> Optional[float]:
        """Calculate 24h price change percentage"""
        if ticker not in self.data:
            return None
        
        ticker_data = self.data[ticker]
        
        # Find current price
        current_mask = ticker_data['timestamp'] == current_timestamp
        if not np.any(current_mask):
            return None
        
        current_idx = np.where(current_mask)[0][0]
        current_close = float(ticker_data[current_idx]['close'])
        
        # Find price 24h ago (1440 minutes)
        past_idx = current_idx - 1440
        if past_idx < 0:
            return None
        
        past_close = float(ticker_data[past_idx]['close'])
        
        if past_close == 0:
            return None
        
        change_pct = ((current_close - past_close) / past_close) * 100
        return change_pct
    
    def get_qualifying_tickers(self, timestamp: np.datetime64) -> List[Tuple[str, float]]:
        """Get tickers with ≥20% absolute 24h change"""
        qualifying = []
        
        for ticker in self.data.keys():
            change = self.calculate_24h_change(ticker, timestamp)
            if change is not None and abs(change) >= 20.0:
                qualifying.append((ticker, change))
        
        # Sort by absolute change (most volatile first)
        qualifying.sort(key=lambda x: abs(x[1]), reverse=True)
        return qualifying
    
    def open_position(self, ticker: str, side: str, leverage: int, size_pct: int, 
                     current_price: float, timestamp: str):
        """Open a new position"""
        if self.position is not None:
            logger.warning("Cannot open position - already have one open")
            return
        
        # Calculate position size
        size = self.balance * (size_pct / 100)
        
        self.position = Position(
            ticker=ticker,
            side=side,
            entry_time=timestamp,
            entry_price=current_price,
            size=size,
            leverage=leverage
        )
        
        logger.debug(f"Opened {side} {ticker} at {current_price:.6f}, size=${size:.2f}, lev={leverage}x")
    
    def close_position(self, current_price: float, timestamp: str, reason: str = "") -> Trade:
        """Close current position and return trade record"""
        if self.position is None:
            return None
        
        pnl_dollar, pnl_pct = self.position.calculate_pnl(current_price)
        
        trade = Trade(
            ticker=self.position.ticker,
            side=self.position.side,
            entry_time=self.position.entry_time,
            entry_price=self.position.entry_price,
            exit_time=timestamp,
            exit_price=current_price,
            size=self.position.size,
            leverage=self.position.leverage,
            pnl=pnl_dollar,
            pnl_pct=pnl_pct,
            reason=reason
        )
        
        # Update balance
        self.balance += pnl_dollar
        
        logger.debug(
            f"Closed {trade.side} {trade.ticker}: "
            f"entry={trade.entry_price:.6f}, exit={trade.exit_price:.6f}, "
            f"PnL=${trade.pnl:.2f} ({trade.pnl_pct:+.2f}%)"
        )
        
        self.position = None
        self.trades.append(trade)
        
        return trade
    
    def build_tick_data(self, timestamp: np.datetime64, day: int, minute_of_day: int,
                        qualifying_tickers: List[Tuple[str, float]]) -> Dict:
        """Build tick data structure matching the challenge format"""
        
        # Account info
        unrealized_pnl = 0.0
        if self.position:
            candle = self.get_candle_at_time(self.position.ticker, timestamp)
            if candle:
                unrealized_pnl, _ = self.position.calculate_pnl(candle['close'])
        
        account = {
            'balance': self.balance,
            'equity': self.balance + unrealized_pnl,
            'unrealized_pnl': unrealized_pnl
        }
        
        # Position info
        position = {'is_open': False}
        if self.position:
            candle = self.get_candle_at_time(self.position.ticker, timestamp)
            current_price = candle['close'] if candle else self.position.entry_price
            pnl_dollar, pnl_pct = self.position.calculate_pnl(current_price)
            
            position = {
                'is_open': True,
                'ticker': self.position.ticker,
                'side': self.position.side,
                'entry_price': self.position.entry_price,
                'entry_time': self.position.entry_time,
                'size': self.position.size,
                'leverage': self.position.leverage,
                'current_price': current_price,
                'unrealized_pnl': pnl_dollar,
                'unrealized_pnl_pct': pnl_pct
            }
        
        # Market data and history
        market_data = {}
        history = {}
        
        tickers_to_include = [t[0] for t in qualifying_tickers]
        if self.position and self.position.ticker not in tickers_to_include:
            tickers_to_include.append(self.position.ticker)
        
        for ticker, change in qualifying_tickers:
            candle = self.get_candle_at_time(ticker, timestamp)
            if candle:
                candle['change_24h_pct'] = change
                market_data[ticker] = candle
        
        # Add position ticker to market data if not already included
        if self.position and self.position.ticker not in market_data:
            candle = self.get_candle_at_time(self.position.ticker, timestamp)
            if candle:
                change = self.calculate_24h_change(self.position.ticker, timestamp)
                candle['change_24h_pct'] = change or 0
                market_data[self.position.ticker] = candle
        
        # Get history for all relevant tickers
        for ticker in tickers_to_include:
            hist = self.get_history(ticker, timestamp, 1440)
            if hist:
                history[ticker] = hist
        
        minutes_remaining = (24 * 60) - minute_of_day  # Minutes until 24:00
        
        return {
            'timestamp': str(timestamp),
            'day': day,
            'minute_of_day': minute_of_day,
            'minutes_remaining': minutes_remaining,
            'account': account,
            'position': position,
            'qualifying_tickers': [t[0] for t in qualifying_tickers],
            'market_data': market_data,
            'history': history
        }
    
    def run(self, start_date: str = '2025-12-01', end_date: str = '2025-12-31',
            verbose: bool = True) -> BacktestResult:
        """
        Run the backtest over the specified date range.
        """
        self.load_data()
        
        # Reset state
        self.balance = config.INITIAL_BALANCE
        self.position = None
        self.trades = []
        self.daily_results = []
        self.equity_curve = [self.balance]
        
        # Reset strategy
        self.strategy.reset()
        
        initial_balance = self.balance
        peak_equity = initial_balance
        max_drawdown = 0.0
        
        # Parse dates
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        day_num = 1
        current_date = start
        
        while current_date <= end:
            date_str = current_date.strftime('%Y-%m-%d')
            day_start_balance = self.balance
            day_trades = []
            
            if verbose:
                logger.info(f"=== Day {day_num}: {date_str} ===")
            
            # Notify strategy of day start
            self.strategy.start_day(day_num, date_str, self.balance)
            
            # Trading window: 08:00 to 24:00 (960 minutes)
            for minute in range(480, 1440):  # 08:00 = minute 480
                hour = minute // 60
                min_of_hour = minute % 60
                
                timestamp = np.datetime64(f'{date_str}T{hour:02d}:{min_of_hour:02d}:00')
                
                # Get qualifying tickers
                qualifying = self.get_qualifying_tickers(timestamp)
                
                if not qualifying:
                    continue
                
                # Build tick data
                tick_data = self.build_tick_data(timestamp, day_num, minute, qualifying)
                
                # Get strategy decision
                decision = self.strategy.decide(tick_data)
                action = decision.get('action', 'HOLD')
                
                # Execute action (next minute's price - simulate real trading)
                next_minute = minute + 1
                if next_minute >= 1440:
                    # End of day - will be force closed
                    continue
                
                next_hour = next_minute // 60
                next_min = next_minute % 60
                next_timestamp = np.datetime64(f'{date_str}T{next_hour:02d}:{next_min:02d}:00')
                
                if action == 'OPEN_LONG' or action == 'OPEN_SHORT':
                    if self.position is None:
                        ticker = decision.get('ticker')
                        leverage = decision.get('leverage', config.DEFAULT_LEVERAGE)
                        size_pct = decision.get('size_pct', config.DEFAULT_SIZE_PCT)
                        
                        # Get execution price (next minute's open)
                        candle = self.get_candle_at_time(ticker, next_timestamp)
                        if candle:
                            exec_price = candle['open']
                            side = 'LONG' if action == 'OPEN_LONG' else 'SHORT'
                            self.open_position(ticker, side, leverage, size_pct, 
                                             exec_price, str(next_timestamp))
                
                elif action == 'CLOSE':
                    if self.position:
                        candle = self.get_candle_at_time(self.position.ticker, next_timestamp)
                        if candle:
                            exec_price = candle['open']
                            trade = self.close_position(exec_price, str(next_timestamp),
                                                       decision.get('reason', ''))
                            if trade:
                                day_trades.append(trade)
                
                # Track equity for drawdown
                current_equity = self.balance
                if self.position:
                    candle = self.get_candle_at_time(self.position.ticker, timestamp)
                    if candle:
                        pnl, _ = self.position.calculate_pnl(candle['close'])
                        current_equity += pnl
                
                self.equity_curve.append(current_equity)
                
                if current_equity > peak_equity:
                    peak_equity = current_equity
                
                drawdown = peak_equity - current_equity
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            # End of day - force close any open position
            if self.position:
                # Get last price of the day
                eod_timestamp = np.datetime64(f'{date_str}T23:59:00')
                candle = self.get_candle_at_time(self.position.ticker, eod_timestamp)
                if candle:
                    trade = self.close_position(candle['close'], str(eod_timestamp), 'EOD force close')
                    if trade:
                        day_trades.append(trade)
            
            # Record daily results
            daily_pnl = self.balance - day_start_balance
            daily_result = DailyResult(
                day=day_num,
                date=date_str,
                starting_balance=day_start_balance,
                ending_balance=self.balance,
                daily_pnl=daily_pnl,
                trades=day_trades
            )
            self.daily_results.append(daily_result)
            
            # Notify strategy
            self.strategy.end_day(day_num, self.balance, daily_pnl)
            
            if verbose:
                logger.info(
                    f"Day {day_num} complete: ${day_start_balance:.2f} -> ${self.balance:.2f} "
                    f"(PnL: ${daily_pnl:+.2f}, {len(day_trades)} trades)"
                )
            
            day_num += 1
            current_date += timedelta(days=1)
        
        # Calculate final statistics
        total_pnl = self.balance - initial_balance
        total_return_pct = (total_pnl / initial_balance) * 100
        
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]
        
        win_rate = len(winning_trades) / len(self.trades) * 100 if self.trades else 0
        
        # Calculate Sharpe ratio (simplified)
        daily_returns = [dr.daily_return_pct for dr in self.daily_results]
        if daily_returns and len(daily_returns) > 1:
            avg_return = np.mean(daily_returns)
            std_return = np.std(daily_returns)
            sharpe = (avg_return / std_return) * np.sqrt(365) if std_return > 0 else 0
        else:
            sharpe = 0
        
        max_drawdown_pct = (max_drawdown / peak_equity) * 100 if peak_equity > 0 else 0
        
        result = BacktestResult(
            initial_balance=initial_balance,
            final_balance=self.balance,
            total_pnl=total_pnl,
            total_return_pct=total_return_pct,
            total_trades=len(self.trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe,
            daily_results=self.daily_results,
            all_trades=self.trades
        )
        
        return result
    
    def print_results(self, result: BacktestResult):
        """Print formatted backtest results"""
        print("\n" + "=" * 60)
        print("BACKTEST RESULTS")
        print("=" * 60)
        
        print(f"\n[PERFORMANCE SUMMARY]")
        print(f"  Initial Balance:    ${result.initial_balance:,.2f}")
        print(f"  Final Balance:      ${result.final_balance:,.2f}")
        print(f"  Total P&L:          ${result.total_pnl:+,.2f}")
        print(f"  Total Return:       {result.total_return_pct:+.2f}%")
        
        print(f"\n[TRADE STATISTICS]")
        print(f"  Total Trades:       {result.total_trades}")
        print(f"  Winning Trades:     {result.winning_trades}")
        print(f"  Losing Trades:      {result.losing_trades}")
        print(f"  Win Rate:           {result.win_rate:.1f}%")
        
        print(f"\n[RISK METRICS]")
        print(f"  Max Drawdown:       ${result.max_drawdown:,.2f}")
        print(f"  Max Drawdown %:     {result.max_drawdown_pct:.2f}%")
        print(f"  Sharpe Ratio:       {result.sharpe_ratio:.2f}")
        
        if result.all_trades:
            avg_win = np.mean([t.pnl for t in result.all_trades if t.pnl > 0]) if result.winning_trades > 0 else 0
            avg_loss = np.mean([t.pnl for t in result.all_trades if t.pnl <= 0]) if result.losing_trades > 0 else 0
            
            print(f"\n[TRADE ANALYSIS]")
            print(f"  Average Win:        ${avg_win:+,.2f}")
            print(f"  Average Loss:       ${avg_loss:+,.2f}")
            
            if avg_loss != 0:
                profit_factor = abs(sum(t.pnl for t in result.all_trades if t.pnl > 0) / 
                                   sum(t.pnl for t in result.all_trades if t.pnl < 0)) if result.losing_trades > 0 else float('inf')
                print(f"  Profit Factor:      {profit_factor:.2f}")
        
        print("\n" + "=" * 60)
        
        # Daily breakdown
        print("\n[DAILY RESULTS]")
        print("-" * 60)
        for dr in result.daily_results:
            marker = "[+]" if dr.daily_pnl >= 0 else "[-]"
            print(f"  {marker} Day {dr.day:2d} ({dr.date}): ${dr.ending_balance:,.2f} "
                  f"({dr.daily_pnl:+.2f}, {len(dr.trades)} trades)")
        
        print("\n" + "=" * 60)


def main():
    """Run backtest"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Backtest trading strategy')
    parser.add_argument('--start', default='2025-12-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', default='2025-12-31', help='End date (YYYY-MM-DD)')
    parser.add_argument('--quiet', action='store_true', help='Suppress verbose output')
    
    args = parser.parse_args()
    
    backtester = Backtester()
    result = backtester.run(
        start_date=args.start,
        end_date=args.end,
        verbose=not args.quiet
    )
    
    backtester.print_results(result)
    
    return result


if __name__ == '__main__':
    main()

