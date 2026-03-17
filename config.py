"""
ThothMind Trading Challenge - Configuration
============================================
Optimized for MOMENTUM CONTINUATION on highly volatile assets (≥20% 24h change).

Key Principle: These are momentum plays - trade WITH the trend, not against it.
"""
import os

# =============================================================================
# API AUTHENTICATION
# =============================================================================
API_KEY: str = os.environ.get("THOTH_API_KEY", "th-203kdm239x9kapqmds9wl2")
# =============================================================================
# TRADING PARAMETERS
# =============================================================================
INITIAL_BALANCE: float = 1000.0

# Leverage settings
# NOTE: 20x is allowed, but we use lower to survive volatility
MAX_LEVERAGE: int = 8       # Reduced from 10 - these are very volatile assets
MIN_LEVERAGE: int = 2       # Minimum 2x to capture moves
DEFAULT_LEVERAGE: int = 4   # Slightly higher base - these are momentum plays

# Position sizing (percentage of balance)
DEFAULT_SIZE_PCT: int = 60  # Increased - capitalize on good signals
MAX_SIZE_PCT: int = 80      # Allow larger sizes on strong signals
MIN_SIZE_PCT: int = 30

# =============================================================================
# RISK MANAGEMENT
# =============================================================================
# Stop loss - WIDER for volatile assets
# Assets that move 20%+ in 24h can easily swing 5% in minutes
STOP_LOSS_PCT: float = 12.0       # Increased from 8% - give room to breathe
TAKE_PROFIT_PCT: float = 30.0     # Increased from 25% - let winners run
TRAILING_STOP_PCT: float = 50.0   # Trail at 50% of peak profit

# Time-based risk management
MIN_MINUTES_BEFORE_EOD: int = 45  # Reduced - can still capture late moves
MAX_POSITION_DURATION_MINUTES: int = 240  # 4 hours max

# Trade management
TRADE_COOLDOWN_MINUTES: int = 10  # Reduced cooldown - act on opportunities
MAX_TRADES_PER_DAY: int = 8       # Allow more trades per day

# =============================================================================
# STRATEGY PARAMETERS - MOMENTUM FOCUSED
# =============================================================================
# Entry confidence threshold
# Lower than before - momentum plays don't need all indicators to align
MIN_CONFIDENCE: float = 0.55  # Reduced from 0.75 - enter earlier in moves

# These are kept for backtester compatibility but not used in main strategy
RSI_PERIOD: int = 14
RSI_OVERSOLD: float = 30.0
RSI_OVERBOUGHT: float = 70.0

EMA_FAST: int = 9
EMA_SLOW: int = 21
EMA_TREND: int = 50

MACD_FAST: int = 12
MACD_SLOW: int = 26
MACD_SIGNAL: int = 9

BOLLINGER_PERIOD: int = 20
BOLLINGER_STD: float = 2.0

VOLUME_MA_PERIOD: int = 20
VOLUME_SPIKE_THRESHOLD: float = 1.5

# Legacy parameter kept for compatibility
MIN_MOMENTUM_SCORE: float = 0.55

# =============================================================================
# SERVER CONFIGURATION
# =============================================================================
SERVER_HOST: str = os.environ.get("HOST", "0.0.0.0")
SERVER_PORT: int = int(os.environ.get("PORT", "5000"))
DEBUG_MODE: bool = os.environ.get("DEBUG", "false").lower() == "true"

# Logging
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
