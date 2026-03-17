"""
ThothMind Trading Challenge - Flask Application
================================================
Main HTTP server implementing all required endpoints.

Endpoints:
- GET  /health  - Health check
- POST /reset   - Reset application state
- POST /start   - Start of trading day
- POST /tick    - Trading decision (main logic)
- POST /end     - End of trading day
"""
import os
import sys
import logging
from functools import wraps
from datetime import datetime
from typing import Callable, Any

from flask import Flask, request, jsonify, Response

import config
from strategy import TradingStrategy

# =============================================================================
# LOGGING SETUP
# =============================================================================
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# APPLICATION SETUP
# =============================================================================
app = Flask(__name__)

# Initialize strategy
strategy = TradingStrategy()

# Request counter for monitoring
request_count = {
    'health': 0,
    'reset': 0,
    'start': 0,
    'tick': 0,
    'end': 0,
    'errors': 0
}


# =============================================================================
# AUTHENTICATION MIDDLEWARE
# =============================================================================
def require_api_key(f: Callable) -> Callable:
    """
    Decorator to validate API key on all endpoints.
    Returns 401 Unauthorized if key is missing or invalid.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs) -> Any:
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            logger.warning("Request missing X-API-Key header")
            request_count['errors'] += 1
            return jsonify({'error': 'Unauthorized'}), 401
        
        if api_key != config.API_KEY:
            logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
            request_count['errors'] += 1
            return jsonify({'error': 'Unauthorized'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


# =============================================================================
# ERROR HANDLERS
# =============================================================================
@app.errorhandler(Exception)
def handle_exception(e: Exception) -> tuple[Response, int]:
    """Global exception handler to prevent crashes"""
    logger.exception(f"Unhandled exception: {e}")
    request_count['errors'] += 1
    return jsonify({
        'error': 'Internal server error',
        'message': str(e)
    }), 500


@app.errorhandler(400)
def bad_request(e) -> tuple[Response, int]:
    """Handle bad request errors"""
    request_count['errors'] += 1
    return jsonify({'error': 'Bad request', 'message': str(e)}), 400


@app.errorhandler(404)
def not_found(e) -> tuple[Response, int]:
    """Handle not found errors"""
    return jsonify({'error': 'Not found'}), 404


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.route('/health', methods=['GET'])
@require_api_key
def health() -> tuple[Response, int]:
    """
    Health check endpoint.
    Called periodically to verify the solution is running.
    """
    request_count['health'] += 1
    logger.debug("Health check requested")
    
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'request_counts': request_count
    }), 200


@app.route('/reset', methods=['POST'])
@require_api_key
def reset() -> tuple[Response, int]:
    """
    Reset endpoint.
    Clears all stored data and returns to initial state.
    """
    request_count['reset'] += 1
    
    try:
        data = request.get_json(silent=True) or {}
        reason = data.get('reason', 'No reason provided')
        
        logger.info(f"Reset requested: {reason}")
        
        # Reset strategy state
        strategy.reset()
        
        # Reset request counters (except this one)
        for key in request_count:
            if key != 'reset':
                request_count[key] = 0
        
        return jsonify({
            'status': 'reset_complete',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200
    
    except Exception as e:
        logger.exception(f"Error during reset: {e}")
        return jsonify({
            'status': 'reset_complete',
            'warning': str(e)
        }), 200


@app.route('/start', methods=['POST'])
@require_api_key
def start() -> tuple[Response, int]:
    """
    Start of trading day endpoint.
    Called at 08:00 UTC each trading day.
    """
    request_count['start'] += 1
    
    try:
        data = request.get_json()
        
        if not data:
            logger.warning("Start called with no data")
            return jsonify({'status': 'ready'}), 200
        
        day = data.get('day', 0)
        date = data.get('date', '')
        initial_balance = data.get('initial_balance', config.INITIAL_BALANCE)
        
        logger.info(f"=== DAY {day} START ({date}) === Balance: ${initial_balance:.2f}")
        
        # Initialize strategy for the day
        strategy.start_day(day, date, initial_balance)
        
        return jsonify({
            'status': 'ready',
            'day': day,
            'date': date
        }), 200
    
    except Exception as e:
        logger.exception(f"Error in start: {e}")
        return jsonify({'status': 'ready'}), 200


@app.route('/tick', methods=['POST'])
@require_api_key
def tick() -> tuple[Response, int]:
    """
    Main trading tick endpoint.
    Called every minute with market data.
    Returns trading decision.
    """
    request_count['tick'] += 1
    
    try:
        data = request.get_json()
        
        if not data:
            logger.warning("Tick called with no data")
            return jsonify({'action': 'HOLD'}), 200
        
        timestamp = data.get('timestamp', '')
        minute_of_day = data.get('minute_of_day', 0)
        minutes_remaining = data.get('minutes_remaining', 0)
        
        # Log periodically (every 60 minutes)
        if minute_of_day % 60 == 0:
            account = data.get('account', {})
            position = data.get('position', {})
            logger.info(
                f"Tick {minute_of_day}/1440 | "
                f"Balance: ${account.get('balance', 0):.2f} | "
                f"Equity: ${account.get('equity', 0):.2f} | "
                f"Position: {position.get('ticker', 'None') if position.get('is_open') else 'None'}"
            )
        
        # Get trading decision from strategy
        decision = strategy.decide(data)
        
        # Validate decision
        action = decision.get('action', 'HOLD')
        
        if action not in ['HOLD', 'OPEN_LONG', 'OPEN_SHORT', 'CLOSE']:
            logger.warning(f"Invalid action from strategy: {action}, defaulting to HOLD")
            return jsonify({'action': 'HOLD'}), 200
        
        # Build response based on action type
        response = {'action': action}
        
        if action in ['OPEN_LONG', 'OPEN_SHORT']:
            # Validate required fields for opening positions
            ticker = decision.get('ticker')
            leverage = decision.get('leverage', config.DEFAULT_LEVERAGE)
            size_pct = decision.get('size_pct', config.DEFAULT_SIZE_PCT)
            
            # Validate ticker is in qualifying list
            qualifying = data.get('qualifying_tickers', [])
            if ticker not in qualifying:
                logger.warning(f"Ticker {ticker} not in qualifying list, defaulting to HOLD")
                return jsonify({'action': 'HOLD'}), 200
            
            # Validate leverage
            leverage = max(config.MIN_LEVERAGE, min(leverage, config.MAX_LEVERAGE))
            
            # Validate size
            size_pct = max(config.MIN_SIZE_PCT, min(size_pct, config.MAX_SIZE_PCT))
            
            response['ticker'] = ticker
            response['leverage'] = leverage
            response['size_pct'] = size_pct
            
            if 'reason' in decision:
                response['reason'] = decision['reason']
            
            logger.info(
                f"ACTION: {action} {ticker} | "
                f"Leverage: {leverage}x | Size: {size_pct}%"
            )
        
        elif action == 'CLOSE':
            if 'reason' in decision:
                response['reason'] = decision['reason']
            logger.info(f"ACTION: CLOSE | Reason: {decision.get('reason', 'N/A')}")
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.exception(f"Error in tick: {e}")
        # Safety: return HOLD on any error
        return jsonify({'action': 'HOLD'}), 200


@app.route('/end', methods=['POST'])
@require_api_key
def end() -> tuple[Response, int]:
    """
    End of trading day endpoint.
    Called at 24:00 UTC. Any open position is force-closed before this call.
    """
    request_count['end'] += 1
    
    try:
        data = request.get_json()
        
        if not data:
            logger.warning("End called with no data")
            return jsonify({'status': 'done'}), 200
        
        day = data.get('day', 0)
        date = data.get('date', '')
        final_balance = data.get('final_balance', 0)
        daily_pnl = data.get('daily_pnl', 0)
        trades_today = data.get('trades_today', 0)
        
        logger.info(
            f"=== DAY {day} END ({date}) === "
            f"Final: ${final_balance:.2f} | "
            f"PnL: ${daily_pnl:+.2f} | "
            f"Trades: {trades_today}"
        )
        
        # Notify strategy of day end
        strategy.end_day(day, final_balance, daily_pnl)
        
        return jsonify({
            'status': 'done',
            'day': day,
            'final_balance': final_balance,
            'daily_pnl': daily_pnl
        }), 200
    
    except Exception as e:
        logger.exception(f"Error in end: {e}")
        return jsonify({'status': 'done'}), 200


# =============================================================================
# ADDITIONAL UTILITY ENDPOINTS (Optional but helpful)
# =============================================================================

@app.route('/', methods=['GET'])
def index() -> tuple[Response, int]:
    """Root endpoint - basic info"""
    return jsonify({
        'name': 'ThothMind Trading Bot',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': [
            'GET /health',
            'POST /reset',
            'POST /start',
            'POST /tick',
            'POST /end'
        ]
    }), 200


@app.route('/stats', methods=['GET'])
@require_api_key
def stats() -> tuple[Response, int]:
    """Statistics endpoint for monitoring"""
    return jsonify({
        'request_counts': request_count,
        'uptime': 'N/A',  # Could track actual uptime
        'strategy_state': {
            'has_state': bool(strategy.state),
            'current_day': strategy.state.get('day', None)
        }
    }), 200


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("ThothMind Trading Bot Starting")
    logger.info("=" * 60)
    logger.info(f"Host: {config.SERVER_HOST}")
    logger.info(f"Port: {config.SERVER_PORT}")
    logger.info(f"Debug: {config.DEBUG_MODE}")
    logger.info(f"API Key: {config.API_KEY[:10]}... (truncated)")
    logger.info("=" * 60)
    
    # Run Flask app
    app.run(
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        debug=config.DEBUG_MODE,
        threaded=True
    )

