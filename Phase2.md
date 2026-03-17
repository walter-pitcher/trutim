# ThothMind Trading Challenge - Phase 2

## Overview

Design and implement an automated trading strategy that trades Binance Futures assets which have moved more than 20% in absolute value over the past 24 hours.

Your solution will receive real-time market data minute-by-minute and must respond with trading decisions. The goal is to maximize your final portfolio value.

---

## Challenge Rules

| Parameter | Value |
|-----------|-------|
| **Initial Balance** | $1,000 |
| **Trading Window** | 08:00 UTC - 24:00 UTC daily |
| **Maximum Leverage** | 20x |
| **Eligible Assets** | Only tickers with ≥20% absolute 24h change |
| **Position Limit** | Only ONE position open at a time |

---

## How It Works

1. You deploy your solution to a publicly accessible endpoint
2. You provide us with your endpoint URL and API key
3. Our runner calls your endpoint every minute with market data from 08:00 to 24:00 UTC
4. Your solution analyzes the data and returns a trading action
5. At the end of each day (24:00 UTC), any open position is **automatically closed**
6. Your final score is based on your ending portfolio value after 31 days

---

## Solution Requirements

### 1. Deploy Your Solution

You must deploy your solution as a **Flask application server** to a publicly accessible HTTPS endpoint.

You can use any hosting provider:
- AWS (EC2, Lambda, ECS)
- Google Cloud (Cloud Run, GCE)
- Azure
- Heroku
- Railway
- Render
- Your own server

**Requirements:**
- Must be a Flask application
- Must be accessible via HTTPS
- Must respond within 5 seconds
- Must be available 24/7 during the challenge period

### 2. Authentication

All requests from our runner will include an API key in the `X-API-Key` header. Your solution must validate this key.

**Example request header:**
```
X-API-Key: your-secret-api-key-here
```

Your solution should:
1. Check for the `X-API-Key` header on every request
2. Return `401 Unauthorized` if the key is missing or invalid
3. Process the request if the key matches

### 3. What to Submit

Send us the following information:

| Field | Description | Example |
|-------|-------------|---------|
| **Endpoint URL** | Your base URL (HTTPS required) | `https://my-trading-bot.example.com` or `https://ip_address:port` etc|
| **API Key** | Secret key for authentication | `sk_live_abc123xyz789` |

We will call your endpoints at:
- `GET {endpoint_url}/health`
- `POST {endpoint_url}/reset`
- `POST {endpoint_url}/start`
- `POST {endpoint_url}/tick`
- `POST {endpoint_url}/end`

---

## Required Endpoints

Your HTTP server must implement these endpoints:

### `GET /health`

Health check endpoint. Called periodically to verify your solution is running.

**Request Headers:**
```
X-API-Key: your-api-key
```

**Response (200 OK):**
```json
{
  "status": "ok"
}
```

**Response (401 Unauthorized) - if API key is invalid:**
```json
{
  "error": "Unauthorized"
}
```

---

### `POST /reset`

Called to reset your application state. Use this to clear any stored data and return to initial state.

**Request Headers:**
```
Content-Type: application/json
X-API-Key: your-api-key
```

**Request Body:**
```json
{
  "reason": "New simulation starting"
}
```

**Response (200 OK):**
```json
{
  "status": "reset_complete"
}
```

---

### `POST /start`

Called at the start of each trading day (08:00 UTC).

**Request Headers:**
```
Content-Type: application/json
X-API-Key: your-api-key
```

**Request Body:**
```json
{
  "day": 15,
  "date": "2025-12-15",
  "initial_balance": 1000.0
}
```

**Response (200 OK):**
```json
{
  "status": "ready"
}
```

---

### `POST /tick`

Called every minute with current market data. **This is where your strategy logic runs.**

The request includes:
- **Current candle** for each qualifying ticker in `market_data`
- **Past 24 hours of candles** (1,440 data points) for each qualifying ticker + the active position ticker in `history`

**Request Headers:**
```
Content-Type: application/json
X-API-Key: your-api-key
```

**Request Body:**
```json
{
  "timestamp": "2025-12-15T10:30:00Z",
  "day": 15,
  "minute_of_day": 630,
  "minutes_remaining": 810,

  "account": {
    "balance": 1050.25,
    "equity": 1075.50,
    "unrealized_pnl": 25.25
  },

  "position": {
    "is_open": true,
    "ticker": "XYZUSDT",
    "side": "LONG",
    "entry_price": 1.200,
    "entry_time": "2025-12-15T09:45:00Z",
    "size": 500.0,
    "leverage": 10,
    "current_price": 1.250,
    "unrealized_pnl": 25.25,
    "unrealized_pnl_pct": 4.17
  },

  "qualifying_tickers": ["XYZUSDT", "ABCUSDT", "DEFUSDT"],

  "market_data": {
    "XYZUSDT": {
      "timestamp": "2025-12-15T10:30:00Z",
      "open": 1.245,
      "high": 1.252,
      "low": 1.240,
      "close": 1.250,
      "volume": 125000.5,
      "change_24h_pct": 28.5
    },
    "ABCUSDT": {
      "timestamp": "2025-12-15T10:30:00Z",
      "open": 0.385,
      "high": 0.390,
      "low": 0.380,
      "close": 0.382,
      "volume": 890000.0,
      "change_24h_pct": -23.6
    }
  },

  "history": {
    "XYZUSDT": [
      ["2025-12-14T10:31:00Z", 1.000, 1.010, 0.995, 1.005, 50000.0],
      ["2025-12-14T10:32:00Z", 1.005, 1.015, 1.000, 1.010, 48000.0],
      "... (1,440 candles total - past 24 hours)",
      ["2025-12-15T10:30:00Z", 1.245, 1.252, 1.240, 1.250, 125000.5]
    ],
    "ABCUSDT": [
      ["2025-12-14T10:31:00Z", 0.500, 0.510, 0.495, 0.505, 80000.0],
      "... (1,440 candles total - past 24 hours)",
      ["2025-12-15T10:30:00Z", 0.385, 0.390, 0.380, 0.382, 890000.0]
    ]
  }
}
```

**History format:** Each candle is an array: `[timestamp, open, high, low, close, volume]`


**Response - Your Trading Decision (200 OK):**
```json
{
  "action": "OPEN_LONG",
  "ticker": "XYZUSDT",
  "leverage": 10,
  "size_pct": 100,
  "reason": "Optional: explain your decision"
}
```

---

### `POST /end`

Called at the end of each trading day (24:00 UTC). Any open position is force-closed before this call.

**Request Headers:**
```
Content-Type: application/json
X-API-Key: your-api-key
```

**Request Body:**
```json
{
  "day": 15,
  "date": "2025-12-15",
  "final_balance": 1082.50,
  "daily_pnl": 32.25,
  "trades_today": 3
}
```

**Response (200 OK):**
```json
{
  "status": "done"
}
```

---

## Action Reference

### Valid Actions

| Action | Description | When Allowed |
|--------|-------------|--------------|
| `HOLD` | Do nothing | Always |
| `OPEN_LONG` | Open a long position (buy) | When no position is open |
| `OPEN_SHORT` | Open a short position (sell) | When no position is open |
| `CLOSE` | Close current position | When a position is open |

### Action Parameters

**For `OPEN_LONG` and `OPEN_SHORT`:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | Yes | `"OPEN_LONG"` or `"OPEN_SHORT"` |
| `ticker` | string | Yes | Must be in `qualifying_tickers` list |
| `leverage` | integer | Yes | 1 to 20 |
| `size_pct` | integer | Yes | 1 to 100 (percentage of available balance) |
| `reason` | string | No | Optional explanation |

**For `CLOSE`:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | Yes | `"CLOSE"` |
| `reason` | string | No | Optional explanation |

**For `HOLD`:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | Yes | `"HOLD"` |

### Example Responses

**Open a long position with 10x leverage using full balance:**
```json
{
  "action": "OPEN_LONG",
  "ticker": "XYZUSDT",
  "leverage": 10,
  "size_pct": 100
}
```

**Open a short position with 5x leverage using 50% of balance:**
```json
{
  "action": "OPEN_SHORT",
  "ticker": "ABCUSDT",
  "leverage": 5,
  "size_pct": 50
}
```

**Close current position:**
```json
{
  "action": "CLOSE"
}
```

**Do nothing:**
```json
{
  "action": "HOLD"
}
```

---

## Important Rules

1. **One Position Only**: You can only have one position open at a time. You must close your current position before opening a new one. **The opening and closing of a position will occur in the next minute after your endpoint sends us the trading decision**

2. **Eligible Tickers Only**: You can only trade tickers that appear in the `qualifying_tickers` list (those with ≥20% 24h change).

3. **End of Day**: All positions are automatically closed at 24:00 UTC. Plan your exits accordingly.

4. **Leverage Risk**: Higher leverage amplifies both gains and losses. A 100% loss will liquidate your position.

5. **Response Time**: Your `/tick` endpoint must respond within **5 seconds**. Timeouts are treated as `HOLD`.

6. **Invalid Actions**: Invalid actions (wrong ticker, invalid leverage, etc.) are ignored and treated as `HOLD`.

7. **API Key Validation**: Always validate the `X-API-Key` header. Requests without a valid key should return `401 Unauthorized`.

8. **Availability**: Your endpoint must be available 24/7 during the challenge. Downtime will result in missed trading opportunities.

---

## PnL Calculation

**Long Position:**
```
PnL % = ((current_price - entry_price) / entry_price) × leverage × 100
PnL $ = position_size × PnL %
```

**Short Position:**
```
PnL % = ((entry_price - current_price) / entry_price) × leverage × 100
PnL $ = position_size × PnL %
```

**Example:**
- Entry: LONG XYZUSDT at $1.00 with 10x leverage, $500 position
- Current price: $1.05
- PnL % = ((1.05 - 1.00) / 1.00) × 10 × 100 = 50%
- PnL $ = $500 × 50% = $250

---


## Submission

### What to Submit

Reply to this email with: stefan@thothmind.ai

1. **Endpoint URL**: Your publicly accessible HTTPS endpoint
   ```
   https://your-address
   ```

2. **API Key**: The secret key we should use in the `X-API-Key` header
   ```
   your-secret-api-key
   ```
3. **Brief Description**: A short paragraph describing your strategy approach
### Submission Format
```
Endpoint URL: https://my-trading-bot.railway.app
API Key: sk_challenge_a1b2c3d4e5f6
Strategy: My strategy uses momentum indicators to identify strong trends...
```
---
## Timeline

| Phase | Date | Description |
|-------|------|-------------|
| **Setup** | Week 1 (26 January - 01 February) | Deploy your solution and submit endpoint |
| **Testing** | Week (02 February - 08 February) | We run the simulation and establish leaderboard |
| **Results** | End of Week 2 | Final rankings announced |
---
