# 🚀 ThothMind Trading Challenge - Phase 2

An automated cryptocurrency trading bot for the ThothMind Trading Challenge. This solution trades Binance Futures assets that have moved more than 20% in the past 24 hours, using a sophisticated multi-indicator momentum strategy.

## 📊 Overview

| Parameter | Value |
|-----------|-------|
| **Initial Balance** | $1,000 |
| **Trading Window** | 08:00 UTC - 24:00 UTC |
| **Maximum Leverage** | 20x (limited to 10x for safety) |
| **Eligible Assets** | Tickers with ≥20% absolute 24h change |
| **Position Limit** | One position at a time |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Flask Server                          │
│                        (app.py)                             │
├─────────────────────────────────────────────────────────────┤
│  /health  │  /reset  │  /start  │  /tick  │  /end          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Trading Strategy                          │
│                    (strategy.py)                            │
├─────────────────────────────────────────────────────────────┤
│  Technical Analyzer  │  Position Manager  │  Risk Manager   │
│   - RSI              │   - Entry Logic    │   - Stop Loss   │
│   - EMA Crossover    │   - Exit Logic     │   - Take Profit │
│   - MACD             │   - Size Calc      │   - Trailing    │
│   - Bollinger Bands  │                    │                 │
│   - Volume Analysis  │                    │                 │
│   - Momentum         │                    │                 │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Configuration                            │
│                     (config.py)                             │
└─────────────────────────────────────────────────────────────┘
```

## 🧠 Trading Strategy

### Multi-Indicator Momentum Strategy

The strategy combines **6 technical indicators** with weighted scoring to generate high-confidence trading signals:

| Indicator | Weight | Purpose |
|-----------|--------|---------|
| **EMA Crossover** | 25% | Trend direction & momentum |
| **MACD** | 20% | Trend changes & momentum |
| **RSI** | 15% | Overbought/oversold conditions |
| **Bollinger Bands** | 15% | Price relative to volatility |
| **Momentum** | 15% | Rate of price change |
| **Volume** | 10% | Confirmation of moves |

### Signal Generation

```
LONG Entry:  All indicators bullish + Confidence ≥ 0.75
SHORT Entry: All indicators bearish + Confidence ≥ 0.75
```

### Risk Management

| Parameter | Value | Description |
|-----------|-------|-------------|
| Stop Loss | 8% | Close position if loss exceeds 8% |
| Take Profit | 25% | Close position if profit exceeds 25% |
| Trailing Stop | 40% | Trail 40% below peak profit |
| EOD Buffer | 60 min | No new positions within 60 min of market close |
| Trade Cooldown | 15 min | Minimum time between trades |
| Max Daily Trades | 10 | Prevent overtrading |

## 📁 Project Structure

```
to-2/
├── app.py                      # Flask server (main entry point)
├── strategy.py                 # Trading strategy & technical analysis
├── backtester.py               # Backtesting engine
├── config.py                   # Configuration parameters
├── december_2025_dataset.npz   # Historical data for backtesting
├── requirements.txt            # Python dependencies
├── Phase2.md                   # Challenge requirements
└── README.md                   # This file
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download the project
cd to-2

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Set your API key as an environment variable:

```bash
# Linux/Mac
export THOTH_API_KEY="your-secret-api-key-here"

# Windows (PowerShell)
$env:THOTH_API_KEY="your-secret-api-key-here"

# Windows (CMD)
set THOTH_API_KEY=your-secret-api-key-here
```

### 3. Run the Server

**Development:**
```bash
python app.py
```

**Production (with Gunicorn):**
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 4. Test Endpoints

```bash
# Health check
curl -H "X-API-Key: th-203kdm239x9kapqmds9wl2" http://localhost:5000/health

# Response: {"status": "ok", "timestamp": "..."}
```

## 📈 Backtesting

Run the backtester to evaluate strategy performance on historical data:

```bash
# Full December 2025 backtest
python backtester.py

# Custom date range
python backtester.py --start 2025-12-01 --end 2025-12-15

# Quiet mode (less output)
python backtester.py --quiet
```

### Backtest Output

```
============================================================
BACKTEST RESULTS
============================================================

[PERFORMANCE SUMMARY]
  Initial Balance:    $1,000.00
  Final Balance:      $X,XXX.XX
  Total P&L:          $+XXX.XX
  Total Return:       +XX.XX%

[TRADE STATISTICS]
  Total Trades:       XX
  Winning Trades:     XX
  Losing Trades:      XX
  Win Rate:           XX.X%

[RISK METRICS]
  Max Drawdown:       $XXX.XX
  Max Drawdown %:     XX.XX%
  Sharpe Ratio:       X.XX
```

## 🔧 Configuration Options

All parameters can be adjusted in `config.py`:

### Trading Parameters
```python
MAX_LEVERAGE = 10          # Maximum leverage (challenge allows 20)
DEFAULT_LEVERAGE = 3       # Default leverage for trades
DEFAULT_SIZE_PCT = 50      # Default position size (% of balance)
```

### Risk Management
```python
STOP_LOSS_PCT = 8.0        # Stop loss threshold (%)
TAKE_PROFIT_PCT = 25.0     # Take profit threshold (%)
TRAILING_STOP_PCT = 40.0   # Trailing stop (% below peak)
```

### Technical Indicators
```python
RSI_PERIOD = 14
RSI_OVERSOLD = 30.0
RSI_OVERBOUGHT = 70.0
EMA_FAST = 9
EMA_SLOW = 21
EMA_TREND = 50
```

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check - returns `{"status": "ok"}` |
| POST | `/reset` | Reset application state |
| POST | `/start` | Called at start of trading day (08:00 UTC) |
| POST | `/tick` | Main trading logic - returns action |
| POST | `/end` | Called at end of trading day (24:00 UTC) |

### Action Responses

```json
// Open long position
{
  "action": "OPEN_LONG",
  "ticker": "XYZUSDT",
  "leverage": 5,
  "size_pct": 50,
  "reason": "Signal: STRONG_BUY, Confidence: 0.85"
}

// Open short position
{
  "action": "OPEN_SHORT",
  "ticker": "ABCUSDT",
  "leverage": 3,
  "size_pct": 40
}

// Close position
{
  "action": "CLOSE",
  "reason": "Take profit triggered at 25.5%"
}

// Do nothing
{
  "action": "HOLD"
}
```

## 🚢 Deployment

### Railway/Render/Heroku

1. Push code to GitHub
2. Connect repository to your platform
3. Set environment variables:
   - `THOTH_API_KEY`: Your secret API key
   - `PORT`: (usually set automatically)

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

### AWS EC2 / GCP / Azure

```bash
# Install dependencies
pip install -r requirements.txt

# Run with Gunicorn (production)
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Or use systemd service for persistence
```

## ⚠️ Important Notes

1. **API Key Security**: Never commit your real API key. Use environment variables.

2. **Response Time**: The `/tick` endpoint must respond within 5 seconds.

3. **Availability**: Your endpoint must be available 24/7 during the challenge.

4. **HTTPS Required**: Production deployment must use HTTPS.

5. **Leverage Risk**: High leverage amplifies both gains and losses. The strategy uses conservative defaults.

## 📊 Strategy Performance Considerations

### Strengths
- ✅ Multiple indicator confirmation reduces false signals
- ✅ Conservative risk management protects capital
- ✅ Volume confirmation validates price movements
- ✅ Adaptive leverage based on volatility
- ✅ Trade cooldown prevents overtrading

### Limitations
- ⚠️ May miss rapid momentum moves due to confirmation requirements
- ⚠️ Trailing stop may exit profitable positions too early
- ⚠️ Conservative sizing may limit upside potential

## 📜 License

MIT License - See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

**Good luck with the ThothMind Trading Challenge!** 🎯


