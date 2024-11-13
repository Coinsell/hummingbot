from typing import Dict, Optional

from hummingbot.core.data_type.common import TradeType
from hummingbot.core.data_type.order_book import OrderBook
from hummingbot.core.data_type.order_book_message import (
    OrderBookMessage,
    OrderBookMessageType
)


class CoinstoreOrderBook(OrderBook):

    @classmethod
    def snapshot_message_from_exchange(cls,
                                       msg: Dict[str, any],
                                       timestamp: float,
                                       metadata: Optional[Dict] = None) -> OrderBookMessage:
        """
        Creates a snapshot message with the order book snapshot message for Coinstore.
        :param msg: the response from Coinstore's API when requesting the order book snapshot
        :param timestamp: the snapshot timestamp
        :param metadata: additional data to include in the snapshot
        :return: a snapshot message with snapshot information from Coinstore
        """
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(OrderBookMessageType.SNAPSHOT, {
            "trading_pair": msg["symbol"],  # Coinstore uses "symbol" for trading pair
            "update_id": msg["lastUpdateId"],  # Check for the relevant ID in Coinstore's snapshot response
            "bids": msg["bids"],  # Order book bids
            "asks": msg["asks"]  # Order book asks
        }, timestamp=timestamp)

    @classmethod
    def diff_message_from_exchange(cls,
                                   msg: Dict[str, any],
                                   timestamp: Optional[float] = None,
                                   metadata: Optional[Dict] = None) -> OrderBookMessage:
        """
        Creates a diff message with changes in the Coinstore order book.
        :param msg: changes in the Coinstore order book
        :param timestamp: timestamp of the difference
        :param metadata: additional data to include in the difference message
        :return: a diff message with changes notified by Coinstore
        """
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(OrderBookMessageType.DIFF, {
            "trading_pair": msg["symbol"],
            "first_update_id": msg["U"],  # Starting update ID for the diff
            "update_id": msg["u"],  # Ending update ID for the diff
            "bids": msg["b"],  # Bid updates
            "asks": msg["a"]  # Ask updates
        }, timestamp=timestamp)

    @classmethod
    def trade_message_from_exchange(cls, msg: Dict[str, any], metadata: Optional[Dict] = None):
        """
        Creates a trade message with details of trade events from Coinstore.
        :param msg: trade event details sent by Coinstore
        :param metadata: additional data to include in the trade message
        :return: a trade message with Coinstore trade details
        """
        if metadata:
            msg.update(metadata)
        ts = msg["event_time"]  # Assuming Coinstore uses "event_time" for trade event timestamp
        return OrderBookMessage(OrderBookMessageType.TRADE, {
            "trading_pair": msg["symbol"],
            "trade_type": float(TradeType.SELL.value) if msg["is_buyer_maker"] else float(TradeType.BUY.value),
            "trade_id": msg["trade_id"],  # Unique trade ID
            "update_id": ts,
            "price": msg["price"],  # Price at which the trade occurred
            "amount": msg["quantity"]  # Quantity traded
        }, timestamp=ts * 1e-3)  # Convert timestamp to seconds if needed