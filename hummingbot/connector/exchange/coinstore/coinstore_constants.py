import sys

from hummingbot.core.api_throttler.data_types import RateLimit
from hummingbot.core.data_type.in_flight_order import OrderState

# Base URLs
REST_URL = "https://api.coinstore.com/api"

WSS_URL = "wss://ws.coinstore.com/s/ws"

# Domain (if necessary for multiple environments)
DEFAULT_DOMAIN = "com"

# Websocket Event Types
DIFF_EVENT_TYPE = "depth"  # For order book depth updates
TRADE_EVENT_TYPE = "trade"  # For trade updates

# Public API Endpoints
LAST_TRADED_PRICE_PATH = "/v1/market/trade/{symbol}"  # Latest trade for a specific symbol
ORDERBOOK_DEPTH_PATH = "/v1/market/depth/{symbol}"  # Order book depth for a symbol
ALL_SYMBOL_PATH = "/v1/ticker/price"  # Latest prices for all trading pairs

# Private API Endpoints (Coinstore-specific)
ACCOUNTS_PATH_URL = "/v1/account"  # Account information endpoint
ORDER_PATH_URL = "/v1/order"  # Place an order
ORDER_CANCEL_PATH_URL = "/v1/order/cancel"  # Cancel an existing order
ORDER_STATUS_PATH_URL = "/v1/order/status"  # Check status of an existing order
MY_TRADES_PATH_URL = "/v1/order/trades"  # User's trade history for orders

# Server Time Path (for server-client time synchronization)
SERVER_TIME_PATH_URL = "/v1/time"

# WebSocket Heartbeat Interval
WS_HEARTBEAT_TIME_INTERVAL = 30  # Send a heartbeat every 30 seconds to maintain connection

# Rate Limits (based on Coinstore’s documented rate limits)
NO_LIMIT = sys.maxsize

RATE_LIMITS = [
    # General
    RateLimit(limit_id=ALL_SYMBOL_PATH, limit=NO_LIMIT, time_interval=1),
    RateLimit(limit_id=ORDERBOOK_DEPTH_PATH, limit=NO_LIMIT, time_interval=1),
    RateLimit(limit_id=LAST_TRADED_PRICE_PATH, limit=NO_LIMIT, time_interval=1),
    # Additional rate limits based on the Coinstore documentation if needed
]

# Order States - Coinstore API Mapped to Hummingbot OrderState
ORDER_STATE = {
    "PENDING_CREATE": OrderState.PENDING_CREATE,  # Order is pending creation
    "NEW": OrderState.OPEN,  # New order, not yet filled
    "PARTIALLY_FILLED": OrderState.PARTIALLY_FILLED,  # Order partially filled
    "FILLED": OrderState.FILLED,  # Order fully filled
    "CANCELLED": OrderState.CANCELED,  # Canceled by user or system
    "REJECTED": OrderState.FAILED,  # Order rejected by system
    "EXPIRED": OrderState.FAILED,  # Order expired without filling
}

# Side Constants
SIDE_BUY = "BUY"
SIDE_SELL = "SELL"

# Time-in-Force Options
TIME_IN_FORCE_GTC = "GTC"  # Good till canceled
TIME_IN_FORCE_IOC = "IOC"  # Immediate or cancel
TIME_IN_FORCE_FOK = "FOK"  # Fill or kill

# Error Handling (Coinstore-specific error codes and messages)
ORDER_NOT_EXIST_ERROR_CODE = 3004  # Error code for "Order does not exist"
ORDER_NOT_EXIST_MESSAGE = "Order does not exist"  # Message for non-existent order

UNKNOWN_ORDER_ERROR_CODE = 3005  # Error code for "Unknown order"
UNKNOWN_ORDER_MESSAGE = "Unknown order"  # Message for unknown order