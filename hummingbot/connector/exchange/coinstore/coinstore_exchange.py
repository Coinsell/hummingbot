from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from bidict import bidict

from hummingbot.client.config.config_helpers import ClientConfigAdapter
from hummingbot.connector.exchange.coinstore import coinstore_constants as CONSTANTS, coinstore_web_utils as web_utils
from hummingbot.connector.exchange.coinstore.coinstore_api_order_book_data_source import CoinstoreAPIOrderBookDataSource
from hummingbot.connector.exchange_py_base import ExchangePyBase
from hummingbot.connector.trading_rule import TradingRule
from hummingbot.connector.utils import combine_to_hb_trading_pair
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.data_type.in_flight_order import InFlightOrder, OrderUpdate, TradeUpdate
from hummingbot.core.data_type.order_book_tracker import OrderBookTrackerDataSource
from hummingbot.core.data_type.trade_fee import TradeFeeBase
from hummingbot.core.utils.estimate_fee import build_trade_fee
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory


class CoinstoreExchange(ExchangePyBase):

    web_utils = web_utils

    def __init__(
        self,
        client_config_map: "ClientConfigAdapter",
        trading_pairs: Optional[List[str]] = None,
        trading_required: bool = True,
    ) -> None:
        self._trading_pairs = trading_pairs or []
        self._trading_required = trading_required
        self._symbol_to_id_map = {}
        super().__init__(client_config_map)

    @property
    def authenticator(self):
        return None

    @property
    def name(self):
        return "coinstore"

    @property
    def rate_limits_rules(self):
        return CONSTANTS.RATE_LIMITS

    @property
    def domain(self):
        return "" #"api.coinstore.com"

    @property
    def client_order_id_max_length(self):
        return 0 #64

    @property
    def client_order_id_prefix(self):
        return "" #"hb"

    @property
    def trading_rules_request_path(self):
        return CONSTANTS.ALL_SYMBOL_PATH

    @property
    def trading_pairs_request_path(self):
        return CONSTANTS.ALL_SYMBOL_PATH

    @property
    def check_network_request_path(self):
        return CONSTANTS.ALL_SYMBOL_PATH

    @property
    def trading_pairs(self):
        return self._trading_pairs

    @property
    def is_cancel_request_in_exchange_synchronous(self) -> bool:
        return False

    @property
    def is_trading_required(self) -> bool:
        return self._trading_required

    def supported_order_types(self) -> List[OrderType]:
        return [OrderType.LIMIT, OrderType.MARKET]

    def _is_request_exception_related_to_time_synchronizer(self, request_exception: Exception):
        return False

    def _is_order_not_found_during_status_update_error(self, status_update_exception: Exception) -> bool:
        return isinstance(status_update_exception, KeyError)

    def _is_order_not_found_during_cancelation_error(self, cancelation_exception: Exception) -> bool:
        return isinstance(cancelation_exception, KeyError)

    def _create_web_assistants_factory(self) -> WebAssistantsFactory:
        return web_utils.build_api_factory(auth=self._auth, throttler=self._throttler)

    def _create_order_book_data_source(self) -> OrderBookTrackerDataSource:
        return CoinstoreAPIOrderBookDataSource(
            trading_pairs=self._trading_pairs, connector=self, api_factory=self._web_assistants_factory
        )

    def _create_user_stream_data_source(self):
        """
        This method will create a WebSocket connection to Coinstore's user stream.
        It will listen for events such as order updates, fills, etc., in real-time.
        """
        async def listen_to_user_stream():
            url = CONSTANTS.USER_STREAM_URL  # WebSocket endpoint URL from Coinstore API documentation
            async with websockets.connect(url) as websocket:
                # Subscribe to the relevant channels for order updates, trades, etc.
                subscribe_message = {
                    "method": "subscribe",
                    "params": {
                        "channel": "user.orders"  # Adjust channel if there are other types of streams
                    }
                }
                await websocket.send(json.dumps(subscribe_message))
                
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)

                    # Process the incoming data (order updates, fills, etc.)
                    if data.get("method") == "orderUpdate":
                        await self._handle_order_update(data["params"])
                    elif data.get("method") == "tradeUpdate":
                        await self._handle_trade_update(data["params"])

        # Run the WebSocket listener
        asyncio.create_task(listen_to_user_stream())

    def _initialize_trading_pair_symbols_from_exchange_info(self, exchange_info: Dict[str, Any]):
        err_code = exchange_info.get("code")
        if err_code != 0:
            err_msg: str = f"Error Code: {err_code} - {exchange_info.get('message')}"
            self.logger().error(
                f"Error initializing trading pair symbols with exchange info response. {err_msg} Response: {exchange_info}"
            )
            return

        mapping = bidict()
        data_list: List[Dict[str, Any]] = exchange_info.get("data")

        for symbol_data in data_list:
            exchange_symbol: str = symbol_data["symbol"]
            if exchange_symbol.endswith("USDT"):  # Only supporting USDT for now
                base_asset, _quote_asset = exchange_symbol.split("USDT")
                mapping[symbol_data["symbol"]] = combine_to_hb_trading_pair(base_asset.upper(), "USDT")
                self._symbol_to_id_map[exchange_symbol] = symbol_data["id"]
        self._set_trading_pair_symbol_map(mapping)

    async def _format_trading_rules(self, exchange_info_dict: Dict[str, Any]) -> List[TradingRule]:
        trading_rules: List[TradingRule] = []
        for symbol_data in exchange_info_dict["data"]:
            base_asset, quote_asset = symbol_data["symbol"].split("USDT")
            trading_rule = TradingRule(
                trading_pair=combine_to_hb_trading_pair(base_asset.upper(), "USDT"),
                min_price_increment=Decimal(symbol_data["tickSize"]),
                min_base_amount_increment=Decimal(symbol_data["lotSize"]),
                price_decimals=4,  # Assuming 4 decimal places for price, adjust based on actual API
                amount_decimals=base_asset.upper(),  # Precision for base asset, adjust as needed
            )
            trading_rules.append(trading_rule)
        return trading_rules

    async def _place_order(
        self,
        order_id: str,
        trading_pair: str,
        amount: Decimal,
        trade_type: TradeType,
        order_type: OrderType,
        price: Decimal,
        **kwargs,
    ) -> Tuple[str, float]:
        # Implement the API call to place an order on Coinstore
        payload = {
            "symbol": self._symbol_to_id_map.get(trading_pair),
            "side": trade_type.value,
            "type": order_type.value,
            "price": str(price),
            "quantity": str(amount),
        }

        response = await self._web_assistants_factory.submit_request(
            "POST", CONSTANTS.PLACE_ORDER_PATH, params=payload
        )

        if response["status"] != "success":
            self.logger().error(f"Error placing order: {response['message']}")
            return None, 0.0

        order_status = response["data"]
        return order_status["orderId"], float(order_status["price"])

    async def _place_cancel(self, order_id: str, tracked_order: InFlightOrder) -> bool:
        # API call to cancel the order on Coinstore
        payload = {"orderId": order_id}
        response = await self._web_assistants_factory.submit_request(
            "POST", CONSTANTS.CANCEL_ORDER_PATH, params=payload
        )

        if response["status"] != "success":
            self.logger().error(f"Error canceling order: {response['message']}")
            return False

        return True

    def _get_fee(
        self,
        base_currency: str,
        quote_currency: str,
        order_type: OrderType,
        order_side: TradeType,
        amount: Decimal,
        price: Decimal,
        is_maker: Optional[bool] = None,
    ) -> TradeFeeBase:
        is_maker = is_maker or (order_type in (OrderType.LIMIT_MAKER, OrderType.LIMIT))
        return build_trade_fee(
            exchange=self.name,
            is_maker=is_maker,
            base_currency=base_currency,
            quote_currency=quote_currency,
            order_type=order_type,
            order_side=order_side,
            amount=amount,
            price=price,
        )

    async def _get_last_traded_price(self, trading_pair: str) -> float:
        # API call to fetch the last traded price from Coinstore
        payload = {
            "symbol": self._symbol_to_id_map.get(trading_pair),
        }

        response = await self._web_assistants_factory.submit_request(
            "GET", CONSTANTS.LAST_TRADE_PATH, params=payload
        )

        if response["status"] != "success":
            self.logger().error(f"Error fetching last traded price: {response['message']}")
            return 0.0

        last_trade = response["data"]
        return float(last_trade["price"])

    async def _update_balances(self):
        # API call to fetch balances from Coinstore
        response = await self._web_assistants_factory.submit_request(
            "GET", CONSTANTS.BALANCES_PATH
        )

        if response["status"] != "success":
            self.logger().error(f"Error fetching balances: {response['message']}")
            return

        balances = response["data"]
        for balance in balances:
            self._balance_map[balance["currency"]] = Decimal(balance["available"])

    async def _all_trade_updates_for_order(self, order: InFlightOrder) -> List[TradeUpdate]:
        # API call to fetch all trade updates for an order
        payload = {"orderId": order.client_order_id}
        response = await self._web_assistants_factory.submit_request(
            "GET", CONSTANTS.TRADE_HISTORY_PATH, params=payload
        )

        if response["status"] != "success":
            self.logger().error(f"Error fetching trade updates: {response['message']}")
            return []

        trade_updates = []
        for trade in response["data"]:
            trade_updates.append(
                TradeUpdate(
                    trade_id=trade["tradeId"],
                    client_order_id=order.client_order_id,
                    price=Decimal(trade["price"]),
                    amount=Decimal(trade["quantity"]),
                    timestamp=trade["timestamp"],
                    trade_type=TradeType.BUY if trade["side"] == "buy" else TradeType.SELL,
                    fee=build_trade_fee(
                        exchange=self.name,
                        is_maker=trade["maker"],
                        base_currency=order.trading_pair.split("-")[0],
                        quote_currency=order.trading_pair.split("-")[1],
                        order_side=TradeType.BUY if trade["side"] == "buy" else TradeType.SELL,
                        amount=Decimal(trade["quantity"]),
                        price=Decimal(trade["price"]),
                    ),
                )
            )
        return trade_updates    

    async def _request_order_status(self, tracked_order: InFlightOrder) -> Optional[OrderUpdate]:
        pass

    async def _update_trading_fees(self):
        pass

    async def _user_stream_event_listener(self):
        pass